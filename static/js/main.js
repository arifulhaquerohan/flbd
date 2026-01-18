// Main JavaScript
document.addEventListener('DOMContentLoaded', function() {
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
});
