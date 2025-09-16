(function () {
    const placeholder = document.getElementById('header-placeholder');
    if (!placeholder) {
        return;
    }

    const scriptElement = document.currentScript;
    const config = window.headerConfig || {};

    const resolveUrl = (path) => {
        try {
            return new URL(path, window.location.href).toString();
        } catch (error) {
            return path;
        }
    };

    let partialUrl = config.partialPath ? resolveUrl(config.partialPath) : null;

    if (!partialUrl) {
        if (scriptElement && scriptElement.src) {
            partialUrl = new URL('../../partials/header.html', scriptElement.src).toString();
        } else {
            partialUrl = resolveUrl('/partials/header.html');
        }
    }

    fetch(partialUrl)
        .then((response) => {
            if (!response.ok) {
                throw new Error(`Falha ao buscar parcial: ${response.status}`);
            }
            return response.text();
        })
        .then((html) => {
            placeholder.innerHTML = html;
            applyHeaderConfig(placeholder, config);
            try {
                delete window.headerConfig;
            } catch (error) {
                window.headerConfig = undefined;
            }
        })
        .catch((error) => {
            console.error('Erro ao carregar cabeçalho compartilhado:', error);
        });

    function applyHeaderConfig(root, config) {
        const { logo = {}, leftLinks = [], rightLinks = [] } = config;
        const navLeft = root.querySelector('.nav-left');
        const navRight = root.querySelector('.nav-right');
        const logoLink = root.querySelector('.logo');
        const logoMain = root.querySelector('.logo-main');
        const logoSub = root.querySelector('.logo-sub');

        if (logoLink && logo.href) {
            logoLink.setAttribute('href', logo.href);
        }

        if (logoLink && logo.ariaLabel) {
            logoLink.setAttribute('aria-label', logo.ariaLabel);
        }

        if (logoLink && logo.className) {
            const classValues = Array.isArray(logo.className)
                ? logo.className
                : String(logo.className).split(' ');

            classValues
                .filter(Boolean)
                .forEach((cls) => logoLink.classList.add(cls));
        }

        if (logoMain && logo.main) {
            logoMain.textContent = logo.main;
        }

        if (logoSub) {
            if (logo.sub) {
                logoSub.textContent = logo.sub;
            } else {
                logoSub.remove();
            }
        }

        const populateLinks = (container, links) => {
            if (!container) {
                return;
            }

            container.innerHTML = '';

            if (!Array.isArray(links)) {
                return;
            }

            links.forEach((link) => {
                if (!link || !link.text) {
                    return;
                }

                const anchor = document.createElement('a');
                anchor.textContent = link.text;
                anchor.href = link.href || '#';

                if (link.className) {
                    anchor.className = link.className;
                }

                if (link.target) {
                    anchor.target = link.target;
                }

                if (link.rel) {
                    anchor.rel = link.rel;
                }

                if (link.ariaLabel) {
                    anchor.setAttribute('aria-label', link.ariaLabel);
                }

                container.appendChild(anchor);
            });
        };

        populateLinks(navLeft, leftLinks);
        populateLinks(navRight, rightLinks);
    }
})();
