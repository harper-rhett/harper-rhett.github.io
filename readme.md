# Converting Video to WebP
ffmpeg -i input_file -vf "scale=iw/2:ih/2" -r 24 -c:v libwebp -lossless 0 -qscale 80 -loop 0 -threads 8 -preset default output_file.webp

- i: Input
- vf: Scale
- r: Framerate
- c: Encoder
- lossless: Compression
- qscale: Quality
- loop: Looping (0 is infinity)
- threads: Cores to run command
- preset: Encoding settings