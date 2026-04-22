/* ==========================================================================
 * booking-modal.js
 * Логика модалки #bookingModal: маска телефона (IMask), AJAX-отправка,
 * анимация shake при невалидной форме, показ success-состояния.
 * Подключается из base.html после Bootstrap и IMask.
 * ========================================================================== */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const form = document.getElementById('bookingForm');
        if (!form) return;

        const successContent = document.getElementById('bookingSuccess');
        const submitBtn = document.getElementById('bookingSubmitBtn');
        const phoneInput = document.getElementById('id_phone');
        const modalHeader = document.querySelector('#bookingModal .modal-header');

        const phoneMask = phoneInput && typeof IMask !== 'undefined'
            ? IMask(phoneInput, { mask: '+{7} (000) 000-00-00' })
            : null;

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            e.stopPropagation();

            if (submitBtn.disabled) return;

            this.classList.remove('was-validated');

            if (phoneMask && !phoneMask.masked.isComplete) {
                phoneInput.setCustomValidity('Введите полный номер телефона');
                phoneInput.classList.add('is-invalid');
            } else if (phoneInput) {
                phoneInput.setCustomValidity('');
                phoneInput.classList.remove('is-invalid');
            }

            if (!this.checkValidity()) {
                this.classList.add('was-validated');
                const modalContent = this.closest('.modal-content');
                if (modalContent) {
                    modalContent.style.animation = 'shake 0.4s ease';
                    setTimeout(() => { modalContent.style.animation = ''; }, 400);
                }
                return;
            }

            const formData = new FormData(this);
            submitBtn.disabled = true;
            const originalBtnHtml = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Отправка...';

            fetch(this.getAttribute('action'), {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                },
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        form.classList.add('d-none');
                        if (modalHeader) modalHeader.classList.add('d-none');
                        if (successContent) successContent.classList.remove('d-none');
                    } else {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnHtml;
                        alert('Ошибка: ' + JSON.stringify(data.errors));
                    }
                })
                .catch((err) => {
                    console.error(err);
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnHtml;
                    alert('Произошла ошибка при соединении с сервером');
                });
        });

        form.querySelectorAll('input, select').forEach((el) => {
            el.addEventListener('input', () => {
                el.classList.remove('is-invalid');
                if (el.checkValidity()) el.setCustomValidity('');
            });
        });
    });
})();
