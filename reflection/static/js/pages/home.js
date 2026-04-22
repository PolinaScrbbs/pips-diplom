/* ==========================================================================
 * home.js — инициализация AOS на главной странице.
 * ========================================================================== */
(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', function () {
        if (typeof AOS !== 'undefined') {
            AOS.init({ duration: 800, once: true });
        }
    });
})();
