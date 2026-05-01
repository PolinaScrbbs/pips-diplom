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

        function qsFromToolbar(toolbarEl, extra) {
            const fd = new FormData(toolbarEl);
            const sp = new URLSearchParams();
            for (const [k, v] of fd.entries()) {
                if (v === null || v === undefined) continue;
                const val = String(v).trim();
                if (!val) continue;
                sp.set(k, val);
            }
            if (extra) {
                Object.keys(extra).forEach((k) => {
                    const v = extra[k];
                    if (v === null || v === undefined) return;
                    const val = String(v).trim();
                    if (!val) { sp.delete(k); return; }
                    sp.set(k, val);
                });
            }
            // по умолчанию видимость "visible" не обязана быть в URL
            if (!sp.get('visibility')) sp.set('visibility', 'visible');
            // сбрасываем page при изменениях фильтров (если не пришло явно)
            if (!extra || !Object.prototype.hasOwnProperty.call(extra, 'page')) {
                sp.delete('page');
            }
            return sp;
        }

        function isAdvancedActive(sp) {
            const minP = (sp.get('min_price') || '').trim();
            const maxP = (sp.get('max_price') || '').trim();
            const sort = (sp.get('sort') || '-created_at').trim();
            return Boolean(minP || maxP || (sort && sort !== '-created_at'));
        }

        function applyStateToUI(sp) {
            // toolbar
            if (toolbar) {
                const searchEl = toolbar.querySelector('input[name="search"]');
                const sortEl = toolbar.querySelector('select[name="sort"]');
                const vis = (sp.get('visibility') || 'visible').trim() || 'visible';
                if (searchEl) searchEl.value = (sp.get('search') || '').trim();
                if (sortEl) sortEl.value = (sp.get('sort') || '-created_at').trim() || '-created_at';
                setActiveChip(toolbar, vis);
            }

            // advanced modal
            const advForm = document.querySelector('[data-role="advanced-filters-form"]');
            if (advForm) {
                const visEl = advForm.querySelector('[data-role="advanced-visibility"]');
                const minEl = advForm.querySelector('[data-role="advanced-min-price"]');
                const maxEl = advForm.querySelector('[data-role="advanced-max-price"]');
                const sortEl = advForm.querySelector('[data-role="advanced-sort"]');
                const sEl = advForm.querySelector('[data-role="advanced-search"]');
                if (visEl) visEl.value = (sp.get('visibility') || 'visible').trim() || 'visible';
                if (minEl) minEl.value = (sp.get('min_price') || '').trim();
                if (maxEl) maxEl.value = (sp.get('max_price') || '').trim();
                if (sortEl) sortEl.value = (sp.get('sort') || '-created_at').trim() || '-created_at';
                if (sEl) sEl.value = (sp.get('search') || '').trim();
            }

            // green dot on advanced filters button
            const advBtn = document.querySelector('[data-role="advanced-filters-btn"]');
            if (advBtn) {
                advBtn.classList.toggle('has-dot', isAdvancedActive(sp));
            }
        }

        async function fetchAndRender(sp) {
            const url = `${window.location.pathname}?${sp.toString()}`;
            const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
            const data = await res.json();
            if (!data || data.status !== 'success') return;
            const root = document.getElementById('mod-results');
            if (root) root.innerHTML = data.html || '';
            // обновим URL (чтобы можно было копировать ссылку)
            window.history.replaceState({}, '', url);
            // синхронизируем UI с текущими параметрами
            applyStateToUI(sp);
            // после подмены DOM нужно заново навесить обработчики на новые элементы
            wireRowClicks();
            wireEditDeleteTriggers();
        }

        function setActiveChip(toolbarEl, visibility) {
            toolbarEl.querySelectorAll('button[data-visibility]').forEach((btn) => {
                btn.classList.toggle('is-active', btn.dataset.visibility === visibility);
            });
        }

        function wireRowClicks() {
            document.querySelectorAll('.service-clickable-row').forEach((row) => {
                if (row.__wiredClick) return;
                row.__wiredClick = true;
                row.addEventListener('click', function (e) {
                    if (!e.target.closest('.mod-actions')) {
                        const url = this.dataset.url;
                        if (url) window.location.href = url;
                    }
                });
                row.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter' || e.key === ' ') {
                        const url = this.dataset.url;
                        if (url) window.location.href = url;
                    }
                });
            });
        }

        function wireEditDeleteTriggers() {
            // edit/delete triggers are bound below too; we keep simple reload-safe binding
            document.querySelectorAll('.edit-service-trigger').forEach((btn) => {
                if (btn.__wiredEdit) return;
                btn.__wiredEdit = true;
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

            document.querySelectorAll('.delete-service-trigger').forEach((btn) => {
                if (btn.__wiredDelete) return;
                btn.__wiredDelete = true;
                btn.addEventListener('click', function (e) {
                    e.stopPropagation();
                    serviceIdToDelete = this.dataset.id;
                    document.getElementById('delete-service-name').innerText = this.dataset.name;
                    deleteModal && deleteModal.show();
                });
            });
        }

        // Автопоиск при вводе (debounce).
        const toolbar = document.getElementById('mod-toolbar');
        const searchInput = toolbar ? toolbar.querySelector('input[name="search"]') : null;
        let searchTimer = null;
        if (toolbar && searchInput) {
            searchInput.addEventListener('input', function () {
                if (searchTimer) window.clearTimeout(searchTimer);
                searchTimer = window.setTimeout(function () {
                    fetchAndRender(qsFromToolbar(toolbar));
                }, 300);
            });
        }

        // chips + sort без перезагрузки
        if (toolbar) {
            // превращаем chips в “кнопки фильтра”, не submit
            toolbar.querySelectorAll('.mod-toolbar__chips button[name="visibility"]').forEach((btn) => {
                btn.type = 'button';
                btn.dataset.visibility = btn.value;
                btn.removeAttribute('name');
            });
            const sortSel = toolbar.querySelector('select[name="sort"]');
            if (sortSel) {
                sortSel.addEventListener('change', function () {
                    fetchAndRender(qsFromToolbar(toolbar));
                });
            }

            toolbar.querySelectorAll('button[data-visibility]').forEach((btn) => {
                btn.addEventListener('click', function () {
                    const vis = this.dataset.visibility || 'visible';
                    setActiveChip(toolbar, vis);
                    fetchAndRender(qsFromToolbar(toolbar, { visibility: vis }));
                });
            });

            // перехватываем submit формы (если нажали Enter в поле)
            toolbar.addEventListener('submit', function (e) {
                e.preventDefault();
                fetchAndRender(qsFromToolbar(toolbar));
            });
        }

        // Расширенные фильтры (модалка) — тоже через AJAX
        const filtersForm = document.getElementById('mod-filters-form');
        if (filtersForm) {
            const resetBtn = filtersForm.querySelector('[data-role="mod-filters-reset"]');
            if (resetBtn) {
                resetBtn.addEventListener('click', function () {
                    // reset полей
                    filtersForm.querySelectorAll('input[name="min_price"], input[name="max_price"], input[name="search"]').forEach((el) => { el.value = ''; });
                    const vis = filtersForm.querySelector('select[name="visibility"]');
                    const sort = filtersForm.querySelector('select[name="sort"]');
                    if (vis) vis.value = 'visible';
                    if (sort) sort.value = '-created_at';
                    fetchAndRender(new URLSearchParams({ visibility: 'visible', sort: '-created_at' }));
                    const modalEl = document.getElementById('filterModal');
                    if (modalEl && typeof bootstrap !== 'undefined') bootstrap.Modal.getOrCreateInstance(modalEl).hide();
                });
            }

            filtersForm.addEventListener('submit', function (e) {
                e.preventDefault();
                const sp = new URLSearchParams(new FormData(filtersForm));
                if (!sp.get('visibility')) sp.set('visibility', 'visible');
                fetchAndRender(sp);
                const modalEl = document.getElementById('filterModal');
                if (modalEl && typeof bootstrap !== 'undefined') bootstrap.Modal.getOrCreateInstance(modalEl).hide();
            });
        }

        const editModalEl = document.getElementById('editServiceModal');
        const deleteModalEl = document.getElementById('deleteConfirmModal');
        const editModal = editModalEl && typeof bootstrap !== 'undefined'
            ? new bootstrap.Modal(editModalEl) : null;
        const deleteModal = deleteModalEl && typeof bootstrap !== 'undefined'
            ? new bootstrap.Modal(deleteModalEl) : null;

        let serviceIdToDelete = null;

        // первичное навешивание кликов на строки
        wireRowClicks();

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
                        row && row.classList.add('is-hidden-row');
                        btn && btn.classList.add('is-hidden-state');
                        if (badge) { badge.className = 'mod-status is-hidden'; badge.innerText = 'Скрыта'; }
                        if (icon) icon.className = 'bi bi-eye-slash';
                    } else {
                        row && row.classList.remove('is-hidden-row');
                        btn && btn.classList.remove('is-hidden-state');
                        if (badge) { badge.className = 'mod-status is-active'; badge.innerText = 'Активна'; }
                        if (icon) icon.className = 'bi bi-eye';
                    }
                });
        };

        // первичные edit/delete обработчики
        wireEditDeleteTriggers();

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

        // пагинация без перезагрузки (делегирование на контейнер результатов)
        const results = document.getElementById('mod-results');
        if (results) {
            results.addEventListener('click', function (e) {
                const a = e.target.closest('a');
                if (!a) return;
                const href = a.getAttribute('href') || '';
                if (!href.startsWith('?')) return;
                e.preventDefault();
                const sp = new URLSearchParams(href.replace(/^\?/, ''));
                fetchAndRender(sp);
            });
        }

        // стартовая синхронизация по текущему URL
        applyStateToUI(new URLSearchParams(window.location.search.replace(/^\?/, '')));

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
