// Main JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const runEnhancements = () => {
        initReveal();
        initLightbox();
    };

    if ('requestIdleCallback' in window) {
        window.requestIdleCallback(runEnhancements, { timeout: 1500 });
    } else {
        window.setTimeout(runEnhancements, 1);
    }
});

function initReveal() {
    const revealElements = document.querySelectorAll('.reveal');
    if (!revealElements.length) return;

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
    // Lightbox is now handled by Alpine.js in base.html
    // We just need to trigger the custom event on click
    document.addEventListener('click', function(e) {
        const target = e.target.closest('.img-expand');
        if (!target) return;
        
        const src = target.getAttribute('src');
        const alt = target.getAttribute('alt') || 'Enlarged view';
        
        if (!src) return;
        
        window.dispatchEvent(new CustomEvent('lightbox-open', { 
            detail: { src, alt } 
        }));
    });
}
