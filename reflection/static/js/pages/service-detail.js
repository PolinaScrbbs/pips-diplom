/* ==========================================================================
 * service-detail.js — AOS + подставляем выбранную услугу в модалку записи.
 * ========================================================================== */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        if (typeof AOS !== 'undefined') {
            AOS.init({ duration: 800, once: true });
        }

        const bookingModal = document.getElementById('bookingModal');
        if (!bookingModal) return;

        bookingModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            if (!button) return;

            const serviceId = button.getAttribute('data-service-id');
            const serviceSelect = bookingModal.querySelector('select[name="service"]');

            if (serviceSelect && serviceId) {
                serviceSelect.value = serviceId;
            }
        });
    });
})();
