/* why-us.js — инициализация AOS на странице "Почему мы". */
(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', function () {
        if (typeof AOS !== 'undefined') {
            AOS.init({ duration: 1000, once: true, offset: 100 });
        }
    });
})();
