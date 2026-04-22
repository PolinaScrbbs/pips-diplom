/* ==========================================================================
 * auth-login.js — показ/скрытие пароля, валидация + shake-анимация.
 * ========================================================================== */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const form = document.getElementById('loginForm');
        const authCard = document.getElementById('authCard');
        const togglePassword = document.querySelector('#togglePassword');
        const passwordInput = document.querySelector('#id_password');

        if (togglePassword && passwordInput) {
            togglePassword.addEventListener('click', function () {
                const isPassword = passwordInput.getAttribute('type') === 'password';
                passwordInput.setAttribute('type', isPassword ? 'text' : 'password');
                this.classList.toggle('bi-eye');
                this.classList.toggle('bi-eye-slash');
            });
        }

        if (!form) return;

        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();

                if (authCard) {
                    authCard.classList.remove('shake');
                    void authCard.offsetWidth; // force reflow
                    authCard.classList.add('shake');
                }
            } else {
                const btn = document.getElementById('submitBtn');
                if (btn) {
                    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Проверка...';
                    btn.classList.add('opacity-75');
                }
            }
            form.classList.add('was-validated');
        }, false);

        form.querySelectorAll('input').forEach((input) => {
            input.addEventListener('input', function () {
                if (this.checkValidity()) {
                    this.classList.remove('is-invalid');
                    authCard && authCard.classList.remove('shake');
                }
            });
        });
    });
})();
