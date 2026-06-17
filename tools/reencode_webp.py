"""
Generated with the help of Claude (Anthropic).

Re-encode oversized animated WebP files in images/ to lossy WebP.

Why: several animations are encoded losslessly at 60 fps with hundreds of
frames, producing files up to 27 MB. Animated WebP decodes frame-by-frame on
the browser's main thread, so these tank the frame rate. Lossy re-encoding (and
optionally halving the frame rate of 50+ fps captures) cuts size and decode cost
dramatically while preserving the original playback duration.

Non-destructive: originals are copied to BACKUP_DIR before anything is
overwritten, and a re-encoded file is only written back if it is smaller.

Usage:
    python tools/reencode_webp.py            # compress all animated webps
    python tools/reencode_webp.py --cap-fps  # also cap >50fps captures to ~30fps
"""
import argparse
import shutil
import struct
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
IMAGES = REPO / "images"
BACKUP_DIR = REPO.parent / "webp_backup_orig"
QUALITY = 72          # lossy quality (0-100); 72 is visually clean for screen captures
METHOD = 4            # 0=fast/larger .. 6=slow/smallest; 4 is the speed/size sweet spot
FPS_CAP_MS = 25       # frames shorter than this (>~40fps) are candidates for capping
CAP_TARGET_MS = 33    # ~30fps when --cap-fps is used


def anmf_durations(path: Path):
    """Read real per-frame durations (ms) from the WebP ANMF chunks."""
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    pos, durs = 12, []
    while pos + 8 <= len(data):
        fourcc = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        payload = pos + 8
        if fourcc == b"ANMF":
            d = data[payload + 12] | (data[payload + 13] << 8) | (data[payload + 14] << 16)
            durs.append(d)
        pos = payload + size + (size & 1)  # chunks are even-padded
    return durs


def reencode(path: Path, cap_fps: bool):
    im = Image.open(path)
    n = getattr(im, "n_frames", 1)
    if n <= 1:
        return None  # not animated, skip

    durations = anmf_durations(path) or [im.info.get("duration") or 40] * n

    frames, out_durations = [], []
    drop_every_other = cap_fps and (sum(durations) / n) < FPS_CAP_MS
    for i in range(n):
        if drop_every_other and i % 2 == 1:
            continue
        im.seek(i)
        frames.append(im.convert("RGBA"))
        # when dropping a frame, fold its time into the kept frame
        out_durations.append(durations[i] + (durations[i + 1] if drop_every_other and i + 1 < n else 0))

    print(f"  encoding {path.relative_to(REPO)} ({len(frames)} frames)...", flush=True)
    tmp = path.with_suffix(".reenc.webp")
    frames[0].save(
        tmp, format="WEBP", save_all=True, append_images=frames[1:],
        duration=out_durations, loop=im.info.get("loop", 0),
        quality=QUALITY, method=METHOD, lossless=False,
    )

    before, after = path.stat().st_size, tmp.stat().st_size
    if after >= before:
        tmp.unlink()
        return (path, before, before, n, len(frames), False)

    rel = path.relative_to(REPO)
    backup = BACKUP_DIR / rel
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(path, backup)
    tmp.replace(path)
    return (path, before, after, n, len(frames), True)


def mb(b):
    return f"{b / 1_048_576:.1f}MB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap-fps", action="store_true",
                    help="halve frame rate of captures faster than ~40fps")
    args = ap.parse_args()

    webps = sorted(IMAGES.rglob("*.webp"))
    total_before = total_after = 0
    print(f"Backups -> {BACKUP_DIR}\n")
    for p in webps:
        res = reencode(p, args.cap_fps)
        if res is None:
            continue
        path, before, after, nframes, kept, changed = res
        total_before += before
        total_after += after
        rel = path.relative_to(REPO)
        if changed:
            fps_note = f" frames {nframes}->{kept}" if kept != nframes else ""
            print(f"  {mb(before):>7} -> {mb(after):>7}  {rel}{fps_note}")
        else:
            print(f"  {mb(before):>7}  (kept, no gain)  {rel}")
    print(f"\nTotal animated WebP: {mb(total_before)} -> {mb(total_after)}")


if __name__ == "__main__":
    main()
