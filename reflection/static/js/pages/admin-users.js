/* ==========================================================================
 * admin-users.js
 * Админ-панель: создание/редактирование пользователей, toggle active.
 * URL-ы берутся из data-атрибутов на корневом контейнере #admin-users-root.
 * ========================================================================== */
(function () {
    'use strict';

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie) {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === name + '=') {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function showErrors(targetId, errors) {
        const el = document.getElementById(targetId);
        if (!el) return;
        const parts = [];
        for (const [field, msgs] of Object.entries(errors || {})) {
            parts.push(`${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`);
        }
        el.textContent = parts.join(' | ') || 'Ошибка валидации';
        el.classList.remove('d-none');
    }

    function getConfig() {
        const root = document.getElementById('admin-users-root');
        if (!root) return null;
        return {
            createUrl: root.dataset.createUrl || '',
            toggleUrl: root.dataset.toggleUrl || '',
            jsonUrl: root.dataset.jsonUrl || '',
            updateUrl: root.dataset.updateUrl || '',
        };
    }

    // Шаблон URL содержит `/0/` как placeholder pk (Django reverse с pk=0).
    function buildUrl(template, id) {
        return template.replace('/0/', `/${id}/`);
    }

    document.addEventListener('DOMContentLoaded', function () {
        const cfg = getConfig();
        if (!cfg) return;

        const csrftoken = getCookie('csrftoken');

        const createForm = document.getElementById('create-user-form');
        if (createForm && cfg.createUrl) {
            createForm.addEventListener('submit', async function (e) {
                e.preventDefault();
                document.getElementById('create-user-errors')?.classList.add('d-none');

                const formData = new FormData(createForm);
                const res = await fetch(cfg.createUrl, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrftoken },
                    body: formData,
                });
                const data = await res.json();
                if (!res.ok || data.status !== 'success') {
                    showErrors('create-user-errors', data.errors);
                    return;
                }
                window.location.reload();
            });
        }

        const editModalEl = document.getElementById('editUserModal');
        const editModal = editModalEl && typeof bootstrap !== 'undefined'
            ? new bootstrap.Modal(editModalEl)
            : null;

        document.querySelectorAll('.toggle-active-trigger').forEach((btn) => {
            btn.addEventListener('click', async function () {
                const uid = this.dataset.id;
                const res = await fetch(buildUrl(cfg.toggleUrl, uid), {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrftoken },
                });
                const data = await res.json();
                if (!res.ok || data.status !== 'success') {
                    alert(data.message || 'Ошибка');
                    return;
                }

                const isActive = !!data.user?.is_active;
                this.classList.toggle('is-active', isActive);
                this.classList.toggle('is-inactive', !isActive);
                this.title = isActive ? 'Деактивировать' : 'Активировать';

                const icon = this.querySelector('i');
                if (icon) {
                    icon.className = `bi ${isActive ? 'bi-toggle-on' : 'bi-toggle-off'}`;
                }

                const row = this.closest('tr');
                if (row) row.classList.toggle('row-inactive', !isActive);
            });
        });

        document.querySelectorAll('.edit-user-trigger').forEach((btn) => {
            btn.addEventListener('click', async function () {
                const uid = this.dataset.id;
                document.getElementById('edit-user-errors')?.classList.add('d-none');
                document.getElementById('edit-user-id').value = uid;
                document.getElementById('edit-password').value = '';
                document.getElementById('edit-password2').value = '';

                const res = await fetch(buildUrl(cfg.jsonUrl, uid));
                const data = await res.json();
                if (!res.ok) {
                    showErrors('edit-user-errors', data.errors || { error: data.message || 'Ошибка' });
                    return;
                }

                document.getElementById('edit-username').value = data.username || '';
                document.getElementById('edit-email').value = data.email || '';
                document.getElementById('edit-phone').value = data.phone || '';
                document.getElementById('edit-role').value = data.role || 'user';

                editModal?.show();
            });
        });

        const editForm = document.getElementById('edit-user-form');
        if (editForm) {
            editForm.addEventListener('submit', async function (e) {
                e.preventDefault();
                document.getElementById('edit-user-errors')?.classList.add('d-none');

                const uid = document.getElementById('edit-user-id').value;
                const formData = new FormData(editForm);

                const res = await fetch(buildUrl(cfg.updateUrl, uid), {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrftoken },
                    body: formData,
                });
                const data = await res.json();
                if (!res.ok || data.status !== 'success') {
                    showErrors('edit-user-errors', data.errors || { error: data.message || 'Ошибка' });
                    return;
                }
                window.location.reload();
            });
        }
    });
})();
