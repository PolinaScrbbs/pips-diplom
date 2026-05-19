/* ==========================================================================
 * auth-register.js — клиентская валидация формы регистрации.
 * ========================================================================== */
(function () {
    'use strict';

    var USERNAME_RE = /^[\w.@+-]+$/;
    var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    var MESSAGES = {
        usernameRequired: 'Введите логин.',
        usernameShort: 'Логин должен содержать не менее 3 символов.',
        usernameLong: 'Логин не может быть длиннее 150 символов.',
        usernamePattern: 'Логин может содержать только буквы, цифры и символы @ . + - _.',
        emailRequired: 'Введите email.',
        emailInvalid: 'Введите корректный адрес email.',
        passwordRequired: 'Введите пароль.',
        passwordShort: 'Пароль должен быть не менее 8 символов.',
        password2Required: 'Подтвердите пароль.',
        passwordMismatch: 'Пароли не совпадают.'
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
        if (value.length < 3) {
            return setFieldState(input, feedbackEl, MESSAGES.usernameShort, false);
        }
        if (value.length > 150) {
            return setFieldState(input, feedbackEl, MESSAGES.usernameLong, false);
        }
        if (!USERNAME_RE.test(value)) {
            return setFieldState(input, feedbackEl, MESSAGES.usernamePattern, false);
        }
        return setFieldState(input, feedbackEl, '', true);
    }

    function validateEmail(input, feedbackEl) {
        var value = (input.value || '').trim();
        if (!value) {
            return setFieldState(input, feedbackEl, MESSAGES.emailRequired, false);
        }
        if (!EMAIL_RE.test(value)) {
            return setFieldState(input, feedbackEl, MESSAGES.emailInvalid, false);
        }
        return setFieldState(input, feedbackEl, '', true);
    }

    function validatePassword1(input, feedbackEl) {
        var value = input.value || '';
        if (!value) {
            return setFieldState(input, feedbackEl, MESSAGES.passwordRequired, false);
        }
        if (value.length < 8) {
            return setFieldState(input, feedbackEl, MESSAGES.passwordShort, false);
        }
        return setFieldState(input, feedbackEl, '', true);
    }

    function validatePassword2(pass1, pass2, feedbackEl) {
        var value = pass2.value || '';
        if (!value) {
            return setFieldState(pass2, feedbackEl, MESSAGES.password2Required, false);
        }
        if (pass1 && pass1.value !== value) {
            return setFieldState(pass2, feedbackEl, MESSAGES.passwordMismatch, false);
        }
        return setFieldState(pass2, feedbackEl, '', true);
    }

    document.addEventListener('DOMContentLoaded', function () {
        var form = document.getElementById('registerForm');
        if (!form) return;

        var username = document.getElementById('id_username');
        var email = document.getElementById('id_email');
        var pass1 = document.getElementById('id_password1');
        var pass2 = document.getElementById('id_password2');
        var authCard = form.closest('.auth-card');

        var usernameFeedback = document.getElementById('usernameError');
        var emailFeedback = document.getElementById('emailError');
        var password1Feedback = document.getElementById('password1Error');
        var password2Feedback = document.getElementById('password2Error');

        function validateAll() {
            var ok = true;
            ok = validateUsername(username, usernameFeedback) && ok;
            ok = validateEmail(email, emailFeedback) && ok;
            ok = validatePassword1(pass1, password1Feedback) && ok;
            ok = validatePassword2(pass1, pass2, password2Feedback) && ok;
            return ok;
        }

        if (username) {
            username.addEventListener('input', function () {
                validateUsername(username, usernameFeedback);
            });
            username.addEventListener('blur', function () {
                validateUsername(username, usernameFeedback);
            });
        }

        if (email) {
            email.addEventListener('input', function () {
                validateEmail(email, emailFeedback);
            });
            email.addEventListener('blur', function () {
                validateEmail(email, emailFeedback);
            });
        }

        if (pass1) {
            pass1.addEventListener('input', function () {
                validatePassword1(pass1, password1Feedback);
                if (pass2 && pass2.value) {
                    validatePassword2(pass1, pass2, password2Feedback);
                }
            });
            pass1.addEventListener('blur', function () {
                validatePassword1(pass1, password1Feedback);
            });
        }

        if (pass2) {
            pass2.addEventListener('input', function () {
                validatePassword2(pass1, pass2, password2Feedback);
            });
            pass2.addEventListener('blur', function () {
                validatePassword2(pass1, pass2, password2Feedback);
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
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Создание аккаунта...';
                btn.classList.add('opacity-75');
            }
        });
    });
})();
