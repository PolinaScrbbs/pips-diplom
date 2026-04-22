/* ==========================================================================
 * reviews-list.js — AOS + Isotope для masonry-сетки отзывов.
 * ========================================================================== */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        if (typeof AOS !== 'undefined') {
            AOS.init({ duration: 800, once: true, offset: 50 });
        }

        const grid = document.querySelector('#reviews-container');
        if (grid && typeof Isotope !== 'undefined') {
            // eslint-disable-next-line no-new
            new Isotope(grid, {
                itemSelector: '.col-md-6',
                layoutMode: 'masonry',
            });
        }
    });
})();
