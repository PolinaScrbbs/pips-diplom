/* ==========================================================================
 * auth-login.js — показ/скрытие пароля, валидация + shake-анимация.
 * ========================================================================== */
(function () {
    'use strict';

    var MESSAGES = {
        usernameRequired: 'Введите логин.',
        passwordRequired: 'Введите пароль.'
    };

    function setFieldState(input, feedbackEl, message, isValid) {
        if (!input) return isValid;

        if (isValid) {
            input.setCustomValidity('');
            input.classList.remove('is-invalid');
        } else {
            input.setCustomValidity(message);
            input.classList.add('is-invalid');
            if (feedbackEl) {
                feedbackEl.textContent = message;
            }
        }
        return isValid;
    }

    function validateUsername(input, feedbackEl) {
        var value = (input.value || '').trim();
        if (!value) {
            return setFieldState(input, feedbackEl, MESSAGES.usernameRequired, false);
        }
        return setFieldState(input, feedbackEl, '', true);
    }

    function validatePassword(input, feedbackEl) {
        var value = input.value || '';
        if (!value) {
            return setFieldState(input, feedbackEl, MESSAGES.passwordRequired, false);
        }
        return setFieldState(input, feedbackEl, '', true);
    }

    document.addEventListener('DOMContentLoaded', function () {
        var form = document.getElementById('loginForm');
        var authCard = document.getElementById('authCard');
        var togglePassword = document.querySelector('#togglePassword');
        var passwordInput = document.querySelector('#id_password');
        var usernameInput = document.querySelector('#id_username');
        var usernameFeedback = document.getElementById('usernameError');
        var passwordFeedback = document.getElementById('passwordError');

        if (togglePassword && passwordInput) {
            function toggleVisibility() {
                var isPassword = passwordInput.getAttribute('type') === 'password';
                passwordInput.setAttribute('type', isPassword ? 'text' : 'password');
                togglePassword.classList.toggle('bi-eye');
                togglePassword.classList.toggle('bi-eye-slash');
                togglePassword.setAttribute(
                    'aria-label',
                    isPassword ? 'Скрыть пароль' : 'Показать пароль'
                );
            }

            togglePassword.addEventListener('click', toggleVisibility);
            togglePassword.addEventListener('keydown', function (event) {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    toggleVisibility();
                }
            });
        }

        if (!form) return;

        function validateAll() {
            var ok = true;
            ok = validateUsername(usernameInput, usernameFeedback) && ok;
            ok = validatePassword(passwordInput, passwordFeedback) && ok;
            return ok;
        }

        if (usernameInput) {
            usernameInput.addEventListener('input', function () {
                validateUsername(usernameInput, usernameFeedback);
                authCard && authCard.classList.remove('shake');
            });
            usernameInput.addEventListener('blur', function () {
                validateUsername(usernameInput, usernameFeedback);
            });
        }

        if (passwordInput) {
            passwordInput.addEventListener('input', function () {
                validatePassword(passwordInput, passwordFeedback);
                authCard && authCard.classList.remove('shake');
            });
            passwordInput.addEventListener('blur', function () {
                validatePassword(passwordInput, passwordFeedback);
            });
        }

        form.addEventListener('submit', function (event) {
            var isValid = validateAll();
            form.classList.add('was-validated');

            if (!isValid) {
                event.preventDefault();
                event.stopPropagation();

                if (authCard) {
                    authCard.classList.remove('shake');
                    void authCard.offsetWidth;
                    authCard.classList.add('shake');
                }

                var firstInvalid = form.querySelector('.is-invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
                return;
            }

            var btn = document.getElementById('submitBtn');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Проверка...';
                btn.classList.add('opacity-75');
            }
        });
    });
})();
