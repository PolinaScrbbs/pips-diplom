/* ==========================================================================
 * profile.js — маска телефона, модалка отзыва, AJAX-отправка.
 * CSRF берём из токена формы (не из шаблонных тегов внутри JS).
 * ========================================================================== */
(function () {
    'use strict';

    function getCsrfToken() {
        const el = document.querySelector('[name=csrfmiddlewaretoken]');
        return el ? el.value : '';
    }

    document.addEventListener('DOMContentLoaded', function () {
        const phoneInput = document.getElementById('settings_phone');
        if (phoneInput && typeof IMask !== 'undefined') {
            IMask(phoneInput, { mask: '+{7} (000) 000-00-00' });
        }

        const reviewModal = document.getElementById('reviewFormModal');
        if (reviewModal) {
            reviewModal.addEventListener('show.bs.modal', (e) => {
                const bookingId = e.relatedTarget
                    ? e.relatedTarget.getAttribute('data-booking-id')
                    : '';
                const hiddenInput = document.getElementById('modal_booking_id');
                if (hiddenInput) hiddenInput.value = bookingId;
            });
        }

        const starsLabels = document.querySelectorAll('.stars-group label');
        const ratingLabelHint = document.getElementById('rating-label');

        if (starsLabels.length && ratingLabelHint) {
            starsLabels.forEach((label) => {
                label.addEventListener('mouseenter', () => {
                    ratingLabelHint.textContent = label.getAttribute('data-hint') || '';
                    ratingLabelHint.classList.replace('bg-light', 'bg-success');
                    ratingLabelHint.classList.replace('text-dark', 'text-white');
                });
                label.addEventListener('mouseleave', () => {
                    const checked = document.querySelector('.stars-group input:checked');
                    if (checked) {
                        const activeLabel = document.querySelector(`label[for="${checked.id}"]`);
                        if (activeLabel) {
                            ratingLabelHint.textContent = activeLabel.getAttribute('data-hint') || '';
                        }
                    } else {
                        ratingLabelHint.textContent = 'Выберите оценку';
                        ratingLabelHint.classList.replace('bg-success', 'bg-light');
                        ratingLabelHint.classList.replace('text-white', 'text-dark');
                    }
                });
            });
        }

        const reviewForm = document.getElementById('reviewCreateForm');
        if (reviewForm) {
            reviewForm.addEventListener('submit', function (e) {
                e.preventDefault();
                const btn = this.querySelector('button[type="submit"]');
                if (btn) btn.disabled = true;

                fetch(this.getAttribute('data-url'), {
                    method: 'POST',
                    body: new FormData(this),
                    headers: { 'X-CSRFToken': getCsrfToken() },
                })
                    .then((res) => res.json())
                    .then((data) => {
                        if (data.ok) {
                            location.reload();
                        } else if (btn) {
                            btn.disabled = false;
                        }
                    });
            });
        }
    });
})();
