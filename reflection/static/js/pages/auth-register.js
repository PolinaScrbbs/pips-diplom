/* ==========================================================================
 * auth-register.js — валидация формы регистрации и совпадения паролей.
 * ========================================================================== */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const form = document.getElementById('registerForm');
        if (!form) return;

        const pass1 = document.getElementById('id_password1');
        const pass2 = document.getElementById('id_password2');

        function validatePasswords() {
            if (!pass1 || !pass2) return;
            if (pass1.value !== pass2.value && pass2.value !== '') {
                pass2.setCustomValidity('Passwords do not match');
                pass2.classList.add('is-invalid');
            } else {
                pass2.setCustomValidity('');
                pass2.classList.remove('is-invalid');
            }
        }

        pass1 && pass1.addEventListener('change', validatePasswords);
        pass2 && pass2.addEventListener('keyup', validatePasswords);

        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
})();
