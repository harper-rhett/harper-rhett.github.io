fetch('navbar.html')
    .then(res => res.text())
    .then(text => {
        let oldelem = document.querySelector("script#navbar");
        let newelem = document.createElement("div");
        newelem.innerHTML = text;

        const currentPage = window.location.pathname.split('/').pop();
        const links = newelem.querySelectorAll('a');
        links.forEach(link => {
            if (link.getAttribute('href') === currentPage) {
                link.classList.add('active');
            }
        });

        oldelem.parentNode.replaceChild(newelem, oldelem);
    })