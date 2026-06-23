/* ==========================================================================
 * profile.js — маска телефона, модалка отзыва, AJAX-отправка.
 * ========================================================================== */
(function () {
    'use strict';

    const FIELD_IDS = {
        relation: 'id_relation',
        text: 'id_text',
    };

    function showReviewError(message) {
        const box = document.getElementById('reviewFormError');
        const text = document.getElementById('reviewFormErrorText');
        if (!box || !text) return;
        text.textContent = message || 'Проверьте правильность заполнения формы.';
        box.classList.remove('d-none');
    }

    function hideReviewError() {
        const box = document.getElementById('reviewFormError');
        if (box) box.classList.add('d-none');
    }

    function clearReviewFieldErrors(form) {
        form.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
        const starsGroup = document.getElementById('reviewStarsGroup');
        if (starsGroup) starsGroup.classList.remove('is-invalid-stars');
    }

    function markReviewFieldErrors(errors) {
        if (!errors || typeof errors !== 'object') return;

        Object.keys(errors).forEach((field) => {
            if (field === 'rating') {
                const starsGroup = document.getElementById('reviewStarsGroup');
                if (starsGroup) starsGroup.classList.add('is-invalid-stars');
                return;
            }
            const inputId = FIELD_IDS[field];
            if (!inputId) return;
            const input = document.getElementById(inputId);
            if (input) input.classList.add('is-invalid');
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        const phoneInput = document.getElementById('settings_phone');
        if (phoneInput && typeof IMask !== 'undefined') {
            IMask(phoneInput, { mask: '+{7} (000) 000-00-00' });
        }

        const reviewModal = document.getElementById('reviewFormModal');
        const reviewForm = document.getElementById('reviewCreateForm');

        if (reviewModal) {
            reviewModal.addEventListener('show.bs.modal', (e) => {
                const bookingId = e.relatedTarget
                    ? e.relatedTarget.getAttribute('data-booking-id')
                    : '';
                const hiddenInput = document.getElementById('modal_booking_id');
                if (hiddenInput) hiddenInput.value = bookingId;
                hideReviewError();
                if (reviewForm) {
                    reviewForm.classList.remove('was-validated');
                    clearReviewFieldErrors(reviewForm);
                }
            });

            reviewModal.addEventListener('hidden.bs.modal', () => {
                if (!reviewForm) return;
                reviewForm.reset();
                reviewForm.classList.remove('was-validated');
                clearReviewFieldErrors(reviewForm);
                hideReviewError();
                const ratingLabelHint = document.getElementById('rating-label');
                if (ratingLabelHint) {
                    ratingLabelHint.textContent = 'Выберите оценку';
                    ratingLabelHint.classList.replace('bg-success', 'bg-light');
                    ratingLabelHint.classList.replace('text-white', 'text-dark');
                }
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

        if (reviewForm) {
            reviewForm.querySelectorAll('input, textarea').forEach((el) => {
                el.addEventListener('input', () => {
                    el.classList.remove('is-invalid');
                    hideReviewError();
                });
            });

            reviewForm.querySelectorAll('input[name="rating"]').forEach((el) => {
                el.addEventListener('change', () => {
                    const starsGroup = document.getElementById('reviewStarsGroup');
                    if (starsGroup) starsGroup.classList.remove('is-invalid-stars');
                    hideReviewError();
                });
            });

            reviewForm.addEventListener('submit', function (e) {
                e.preventDefault();
                e.stopPropagation();

                const btn = this.querySelector('button[type="submit"]');
                if (btn && btn.disabled) return;

                hideReviewError();
                clearReviewFieldErrors(this);
                this.classList.remove('was-validated');

                const bookingInput = document.getElementById('modal_booking_id');
                if (!bookingInput || !bookingInput.value) {
                    showReviewError('Не удалось определить запись. Закройте окно и попробуйте снова.');
                    return;
                }

                if (!this.checkValidity()) {
                    this.classList.add('was-validated');
                    const textInput = document.getElementById('id_text');
                    if (textInput && !textInput.checkValidity()) {
                        textInput.classList.add('is-invalid');
                        showReviewError('Текст отзыва должен быть не менее 10 символов.');
                    } else {
                        showReviewError('Заполните все обязательные поля.');
                    }
                    const modalContent = this.closest('.modal-content');
                    if (modalContent) {
                        modalContent.style.animation = 'shake 0.4s ease';
                        setTimeout(() => { modalContent.style.animation = ''; }, 400);
                    }
                    return;
                }

                const formData = new FormData(this);
                if (btn) {
                    btn.disabled = true;
                    btn.dataset.originalHtml = btn.innerHTML;
                    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Отправка...';
                }

                fetch(this.getAttribute('data-url'), {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                })
                    .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
                    .then(({ ok, data }) => {
                        if (ok && data.ok) {
                            location.reload();
                            return;
                        }

                        const message = data.message || 'Не удалось отправить отзыв.';
                        showReviewError(message);
                        markReviewFieldErrors(data.errors);

                        if (btn) {
                            btn.disabled = false;
                            btn.innerHTML = btn.dataset.originalHtml || 'Опубликовать';
                        }

                        const modalContent = reviewForm.closest('.modal-content');
                        if (modalContent) {
                            modalContent.style.animation = 'shake 0.4s ease';
                            setTimeout(() => { modalContent.style.animation = ''; }, 400);
                        }
                    })
                    .catch(() => {
                        showReviewError('Произошла ошибка при соединении с сервером.');
                        if (btn) {
                            btn.disabled = false;
                            btn.innerHTML = btn.dataset.originalHtml || 'Опубликовать';
                        }
                    });
            });
        }
    });
})();
