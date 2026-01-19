// Main JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const runEnhancements = () => {
        initReveal();
        initLightbox();
    };

    // Defer non-critical UI work until the browser is idle.
    if ('requestIdleCallback' in window) {
        window.requestIdleCallback(runEnhancements, { timeout: 1500 });
    } else {
        window.setTimeout(runEnhancements, 1);
    }
});

function initReveal() {
    const revealElements = document.querySelectorAll('.reveal');
    if (!revealElements.length) {
        return;
    }

    if (!('IntersectionObserver' in window)) {
        revealElements.forEach((el) => el.classList.add('is-visible'));
        return;
    }

    const observer = new IntersectionObserver(
        (entries, obs) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    obs.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.18 }
    );

    revealElements.forEach((el) => observer.observe(el));
}

function initLightbox() {
    const lightbox = document.getElementById('imageLightbox');
    const lightboxImg = document.getElementById('lightboxImage');
    if (!lightbox || !lightboxImg || !window.bootstrap || !bootstrap.Modal) {
        return;
    }

    const modal = bootstrap.Modal.getOrCreateInstance(lightbox);
    document.addEventListener('click', function(e) {
        const target = e.target.closest('.img-expand');
        if (!target) {
            return;
        }
        const src = target.getAttribute('src');
        if (!src) {
            return;
        }
        lightboxImg.setAttribute('src', src);
        lightboxImg.setAttribute('alt', target.getAttribute('alt') || 'Enlarged view');
        modal.show();
    });
}
