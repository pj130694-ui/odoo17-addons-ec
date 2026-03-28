// Theme Trionica – Homepage Animations & Interactions
// NOTE: No @odoo-module pragma. This file is loaded via web.assets_frontend_lazy (deferred).
// By the time it executes, DOMContentLoaded has already fired. Run code directly.

// Shim: Odoo 17 website core llama $.fn.compensateScrollbar (Bootstrap 4) pero
// Odoo 17 usa Bootstrap 5 que lo eliminó. Esto previene el TypeError en resize.
if (window.jQuery && !$.fn.compensateScrollbar) {
    $.fn.compensateScrollbar = function () { return this; };
}

(function () {
    // Only run on pages that have tio-fade-up elements
    const fadeEls = document.querySelectorAll('.tio-fade-up');
    if (fadeEls.length) {
        const fadeObserver = new IntersectionObserver((entries) => {
            entries.forEach(e => {
                if (e.isIntersecting) {
                    e.target.classList.add('tio-visible');
                    fadeObserver.unobserve(e.target);
                }
            });
        }, { threshold: 0.1 });

        fadeEls.forEach(el => fadeObserver.observe(el));
    }

    // ── Animated stat counters ───────────────────────────────
    function animateCounter(el) {
        const target = parseInt(el.getAttribute('data-target'), 10);
        const duration = 1800;
        const steps = 60;
        const increment = target / steps;
        let current = 0;
        const timer = setInterval(() => {
            current = Math.min(current + increment, target);
            el.textContent = Math.floor(current).toLocaleString('es-EC') + '+';
            if (current >= target) {
                el.textContent = target.toLocaleString('es-EC') + '+';
                clearInterval(timer);
            }
        }, duration / steps);
    }

    const statsSection = document.querySelector('.tio-stats');
    if (statsSection) {
        const statsObserver = new IntersectionObserver((entries) => {
            entries.forEach(e => {
                if (e.isIntersecting) {
                    e.target.querySelectorAll('[data-target]').forEach(animateCounter);
                    statsObserver.unobserve(e.target);
                }
            });
        }, { threshold: 0.3 });
        statsObserver.observe(statsSection);
    }

    // ── Category pill filter (visual only) ──────────────────
    document.querySelectorAll('.tio-cat-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.tio-cat-pill').forEach(p => {
                p.classList.remove('tio-cat-pill--active');
            });
            pill.classList.add('tio-cat-pill--active');
        });
    });

    // ── Smooth scroll for anchor links ──────────────────────
    document.querySelectorAll('a[href^="#tio-"]').forEach(a => {
        a.addEventListener('click', (e) => {
            const target = document.querySelector(a.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}());
