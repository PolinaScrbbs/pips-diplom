/* ==========================================================================
 * services-moderator.js
 * Управление услугами: toggle visibility, создание, редактирование, удаление.
 * URL-ы и токены берутся из data-атрибутов на корневом контейнере,
 * чтобы шаблонные теги Django не жили внутри JS.
 * ========================================================================== */
(function () {
    'use strict';

    function getCsrfToken() {
        const el = document.querySelector('[name=csrfmiddlewaretoken]');
        return el ? el.value : '';
    }

    function getRootConfig() {
        const root = document.getElementById('services-moderator-root');
        if (!root) return null;
        return {
            toggleUrl: root.dataset.toggleUrl || '',
            jsonUrl: root.dataset.jsonUrl || '',
            updateUrl: root.dataset.updateUrl || '',
            deleteUrl: root.dataset.deleteUrl || '',
            createUrl: root.dataset.createUrl || '',
        };
    }

    // Шаблон содержит `/0/` как placeholder pk (Django reverse с pk=0).
    function buildUrl(template, id) {
        return template.replace('/0/', `/${id}/`);
    }

    document.addEventListener('DOMContentLoaded', function () {
        const cfg = getRootConfig();
        if (!cfg) return;

        const editModalEl = document.getElementById('editServiceModal');
        const deleteModalEl = document.getElementById('deleteConfirmModal');
        const editModal = editModalEl && typeof bootstrap !== 'undefined'
            ? new bootstrap.Modal(editModalEl) : null;
        const deleteModal = deleteModalEl && typeof bootstrap !== 'undefined'
            ? new bootstrap.Modal(deleteModalEl) : null;

        let serviceIdToDelete = null;

        document.querySelectorAll('.service-clickable-row').forEach((row) => {
            row.addEventListener('click', function (e) {
                if (!e.target.closest('.actions-wrapper')) {
                    const url = this.dataset.url;
                    if (url) window.location.href = url;
                }
            });
        });

        window.toggleVisibility = function (serviceId) {
            fetch(buildUrl(cfg.toggleUrl, serviceId), {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.status !== 'success') return;

                    const row = document.getElementById(`service-row-${serviceId}`);
                    const btn = document.getElementById(`toggle-btn-${serviceId}`);
                    const badge = document.getElementById(`status-badge-${serviceId}`);
                    const icon = btn ? btn.querySelector('i') : null;

                    if (data.is_hidden) {
                        row && row.classList.add('row-hidden');
                        btn && btn.classList.add('is-hidden');
                        if (badge) { badge.className = 'badge bg-secondary'; badge.innerText = 'Скрыта'; }
                        if (icon) icon.className = 'bi bi-eye-slash';
                    } else {
                        row && row.classList.remove('row-hidden');
                        btn && btn.classList.remove('is-hidden');
                        if (badge) { badge.className = 'badge bg-success'; badge.innerText = 'Активна'; }
                        if (icon) icon.className = 'bi bi-eye';
                    }
                });
        };

        document.querySelectorAll('.edit-service-trigger').forEach((btn) => {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                const sid = this.dataset.id;
                fetch(buildUrl(cfg.jsonUrl, sid))
                    .then((res) => res.json())
                    .then((data) => {
                        document.getElementById('edit-service-id').value = data.id;
                        document.getElementById('edit-name').value = data.name;
                        document.getElementById('edit-price').value = data.price;
                        document.getElementById('edit-duration').value = data.duration;
                        document.getElementById('edit-short-description').value = data.short_description;
                        document.getElementById('edit-description').value = data.description;
                        editModal && editModal.show();
                    });
            });
        });

        const editForm = document.getElementById('edit-service-form');
        if (editForm) {
            editForm.addEventListener('submit', function (e) {
                e.preventDefault();
                const sid = document.getElementById('edit-service-id').value;
                fetch(buildUrl(cfg.updateUrl, sid), {
                    method: 'POST',
                    body: new FormData(this),
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCsrfToken(),
                    },
                })
                    .then((res) => res.json())
                    .then((data) => {
                        if (data.status === 'success') location.reload();
                        else alert('Ошибка при сохранении');
                    });
            });
        }

        const createForm = document.getElementById('create-service-form');
        if (createForm && cfg.createUrl) {
            createForm.addEventListener('submit', function (e) {
                e.preventDefault();
                fetch(cfg.createUrl, {
                    method: 'POST',
                    body: new FormData(this),
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                })
                    .then((res) => res.json())
                    .then((data) => {
                        if (data.status === 'success') location.reload();
                        else alert('Ошибка при создании');
                    });
            });
        }

        document.querySelectorAll('.delete-service-trigger').forEach((btn) => {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                serviceIdToDelete = this.dataset.id;
                document.getElementById('delete-service-name').innerText = this.dataset.name;
                deleteModal && deleteModal.show();
            });
        });

        const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', function () {
                if (!serviceIdToDelete) return;
                fetch(buildUrl(cfg.deleteUrl, serviceIdToDelete), {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                })
                    .then((res) => res.json())
                    .then((data) => {
                        if (data.status === 'success') location.reload();
                    });
            });
        }
    });
})();
