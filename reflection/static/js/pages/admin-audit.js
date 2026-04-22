/* ==========================================================================
 * admin-audit.js
 * Аудит-журнал: фильтрация, infinite-load, diff-модалка.
 * URL-ы приходят через data-атрибуты на #admin-audit-root.
 * ========================================================================== */
(function () {
    'use strict';

    const ACTION_LABELS = {
        create: 'Создание',
        update: 'Изменение',
        delete: 'Удаление',
        impersonate: 'Вход за пользователя',
        stop_impersonate: 'Возврат из impersonation',
    };
    const ACTION_ICONS = {
        create: 'bi-plus-circle',
        update: 'bi-pencil-square',
        delete: 'bi-trash',
        impersonate: 'bi-incognito',
        stop_impersonate: 'bi-box-arrow-left',
    };

    function escapeHtml(s) {
        if (s === null || s === undefined) return '';
        return String(s)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }

    function fmtDateTime(iso) {
        try {
            const d = new Date(iso);
            return d.toLocaleString('ru-RU', {
                year: 'numeric', month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit', second: '2-digit',
            });
        } catch { return iso; }
    }

    function debounce(fn, delay) {
        let t = null;
        return function (...args) {
            clearTimeout(t);
            t = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    document.addEventListener('DOMContentLoaded', function () {
        const root = document.getElementById('admin-audit-root');
        if (!root) return;

        const cfg = {
            dataUrl: root.dataset.dataUrl,
            filtersUrl: root.dataset.filtersUrl,
            detailUrl: root.dataset.detailUrl,
        };

        const timelineEl = root.querySelector('[data-role="timeline"]');
        const emptyEl = root.querySelector('[data-role="empty"]');
        const paginationEl = root.querySelector('[data-role="pagination"]');
        const statusEl = root.querySelector('[data-role="status"]');
        const totalEl = root.querySelector('[data-role="total"]');
        const todayEl = root.querySelector('[data-role="today"]');

        const entitySelect = root.querySelector('[data-role="entity"]');
        const actorInput = root.querySelector('[data-role="actor"]');
        const actorsList = document.getElementById('audit-actors-list');
        const queryInput = root.querySelector('[data-role="query"]');
        const fromInput = root.querySelector('[data-role="from"]');
        const toInput = root.querySelector('[data-role="to"]');
        const resetBtn = root.querySelector('[data-role="reset"]');
        const chipButtons = root.querySelectorAll('[data-action-filter]');

        const modal = root.querySelector('[data-role="modal"]');
        const modalBody = root.querySelector('[data-role="modal-body"]');
        const modalMeta = root.querySelector('[data-role="modal-meta"]');
        const modalDiff = root.querySelector('[data-role="modal-diff"]');
        const modalCloseEls = root.querySelectorAll('[data-role="modal-close"]');

        const state = {
            action: 'ALL',
            entity: 'ALL',
            actor: '',
            q: '',
            from: '',
            to: '',
            page: 1,
            loading: false,
        };

        function buildParams(page) {
            const p = new URLSearchParams();
            if (state.action && state.action !== 'ALL') p.set('action', state.action);
            if (state.entity && state.entity !== 'ALL') p.set('entity', state.entity);
            if (state.actor) p.set('actor', state.actor);
            if (state.q) p.set('q', state.q);
            if (state.from) p.set('from', state.from);
            if (state.to) p.set('to', state.to);
            p.set('page', String(page));
            return p;
        }

        function renderEntry(e) {
            const icon = ACTION_ICONS[e.action] || 'bi-activity';
            const actionLabel = ACTION_LABELS[e.action] || e.action;
            const fields = e.changed_fields && e.changed_fields.length
                ? `<span class="audit-tag tag-fields"><i class="bi bi-diagram-2"></i>${e.changed_fields.length} поля</span>`
                : '';
            const ip = e.ip_address
                ? `<span class="audit-tag tag-ip">${escapeHtml(e.ip_address)}</span>`
                : '';
            const entityText = e.entity_id
                ? `${escapeHtml(e.entity_label)} · ${escapeHtml(e.entity_repr || ('#' + e.entity_id))}`
                : escapeHtml(e.entity_repr || '—');
            const roleLabel = e.actor_role
                ? `<span class="audit-tag tag-role"><i class="bi bi-person-badge"></i>${escapeHtml(e.actor_role)}</span>`
                : '';

            return `
                <li class="audit-item" data-action="${escapeHtml(e.action)}" data-id="${e.id}" tabindex="0">
                    <div class="audit-item-icon"><i class="bi ${icon}"></i></div>
                    <div class="audit-item-head">
                        <span class="audit-item-title">${escapeHtml(actionLabel)} · ${entityText}</span>
                        <span class="audit-item-time">${escapeHtml(fmtDateTime(e.created_at))}</span>
                    </div>
                    <div class="audit-item-body">
                        <span class="audit-tag tag-actor"><i class="bi bi-person"></i>${escapeHtml(e.actor)}</span>
                        ${roleLabel}
                        ${fields}
                        ${ip}
                    </div>
                </li>`;
        }

        function updateKpi(total) {
            totalEl.textContent = total.toLocaleString('ru-RU');
        }

        async function fetchTodayCount() {
            const t = new Date().toISOString().slice(0, 10);
            const p = new URLSearchParams();
            p.set('from', t);
            p.set('to', t);
            p.set('page', '1');
            try {
                const res = await fetch(`${cfg.dataUrl}?${p.toString()}`);
                const data = await res.json();
                todayEl.textContent = (data.total || 0).toLocaleString('ru-RU');
            } catch { todayEl.textContent = '—'; }
        }

        function renderPagination(data) {
            paginationEl.innerHTML = '';
            const totalPages = data.total_pages || 0;
            if (totalPages <= 1) return;

            const frag = document.createDocumentFragment();

            function pageBtn({ label, page, disabled, active, title }) {
                const b = document.createElement('button');
                b.type = 'button';
                b.className = 'audit-page-btn' + (active ? ' active' : '');
                b.innerHTML = label;
                if (title) b.title = title;
                if (disabled) b.disabled = true;
                if (!disabled && !active) {
                    b.addEventListener('click', () => goToPage(page));
                }
                return b;
            }

            frag.appendChild(pageBtn({
                label: '<i class="bi bi-chevron-left"></i>',
                page: data.page - 1,
                disabled: !data.has_prev,
                title: 'Предыдущая страница',
            }));

            (data.page_range || []).forEach((p) => {
                if (p === 0) {
                    const el = document.createElement('span');
                    el.className = 'audit-page-ellipsis';
                    el.textContent = '…';
                    frag.appendChild(el);
                } else {
                    frag.appendChild(pageBtn({
                        label: String(p),
                        page: p,
                        active: p === data.page,
                    }));
                }
            });

            frag.appendChild(pageBtn({
                label: '<i class="bi bi-chevron-right"></i>',
                page: data.page + 1,
                disabled: !data.has_next,
                title: 'Следующая страница',
            }));

            paginationEl.appendChild(frag);
        }

        function goToPage(page) {
            if (page < 1) return;
            state.page = page;
            load();
            // Скролл вверх к заголовку, если ушли далеко вниз.
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        async function load(resetPage = false) {
            if (state.loading) return;
            state.loading = true;
            if (resetPage) state.page = 1;

            timelineEl.style.opacity = '0.5';
            statusEl.textContent = 'Загрузка…';

            const url = `${cfg.dataUrl}?${buildParams(state.page).toString()}`;
            try {
                const res = await fetch(url);
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const data = await res.json();

                timelineEl.innerHTML = '';
                if (!(data.entries || []).length) {
                    emptyEl.hidden = false;
                    paginationEl.innerHTML = '';
                    statusEl.textContent = '';
                    totalEl.textContent = '0';
                    return;
                }
                emptyEl.hidden = true;

                timelineEl.insertAdjacentHTML('beforeend', data.entries.map(renderEntry).join(''));
                updateKpi(data.total || 0);
                renderPagination(data);

                const from = data.index_from || 0;
                const to = data.index_to || 0;
                statusEl.textContent = data.total
                    ? `${from}–${to} из ${data.total} · страница ${data.page} из ${data.total_pages}`
                    : '';
            } catch (err) {
                statusEl.textContent = 'Ошибка загрузки';
                console.error(err);
            } finally {
                timelineEl.style.opacity = '1';
                state.loading = false;
            }
        }

        async function loadFilterLists() {
            try {
                const res = await fetch(cfg.filtersUrl);
                const data = await res.json();
                // Сущности
                const currentEntity = entitySelect.value;
                entitySelect.innerHTML = '<option value="ALL">Все</option>' +
                    (data.entities || [])
                        .map((e) => `<option value="${escapeHtml(e.value)}">${escapeHtml(e.label)}</option>`)
                        .join('');
                entitySelect.value = currentEntity;
                // Акторы — в datalist
                if (actorsList) {
                    actorsList.innerHTML = (data.actors || [])
                        .map((a) => `<option value="${escapeHtml(a)}"></option>`).join('');
                }
            } catch (err) {
                console.warn('filters load failed', err);
            }
        }

        // --- Event wiring ------------------------------------------------
        chipButtons.forEach((btn) => {
            btn.addEventListener('click', () => {
                chipButtons.forEach((b) => b.classList.remove('active'));
                btn.classList.add('active');
                state.action = btn.dataset.actionFilter;
                load(true);
            });
        });

        entitySelect.addEventListener('change', () => {
            state.entity = entitySelect.value;
            load(true);
        });

        const onActorInput = debounce(() => {
            state.actor = actorInput.value.trim();
            load(true);
        }, 250);
        actorInput.addEventListener('input', onActorInput);

        const onQueryInput = debounce(() => {
            state.q = queryInput.value.trim();
            load(true);
        }, 280);
        queryInput.addEventListener('input', onQueryInput);

        fromInput.addEventListener('change', () => { state.from = fromInput.value; load(true); });
        toInput.addEventListener('change', () => { state.to = toInput.value; load(true); });

        resetBtn.addEventListener('click', () => {
            state.action = 'ALL'; state.entity = 'ALL';
            state.actor = ''; state.q = ''; state.from = ''; state.to = '';
            chipButtons.forEach((b) => b.classList.toggle('active', b.dataset.actionFilter === 'ALL'));
            entitySelect.value = 'ALL';
            actorInput.value = ''; queryInput.value = '';
            fromInput.value = ''; toInput.value = '';
            load(true);
        });

        // --- Modal -------------------------------------------------------
        function openModal(entry, detail) {
            modalMeta.innerHTML = `
                <dl>
                    <dt>Когда</dt><dd>${escapeHtml(fmtDateTime(detail.created_at))}</dd>
                </dl>
                <dl>
                    <dt>Инициатор</dt><dd>${escapeHtml(detail.actor)}${detail.actor_role ? ' · ' + escapeHtml(detail.actor_role) : ''}</dd>
                </dl>
                <dl>
                    <dt>Действие</dt><dd>${escapeHtml(ACTION_LABELS[detail.action] || detail.action)}</dd>
                </dl>
                <dl>
                    <dt>Объект</dt><dd>${escapeHtml(detail.entity_label)} #${escapeHtml(String(detail.entity_id || ''))} · ${escapeHtml(detail.entity_repr)}</dd>
                </dl>
                <dl>
                    <dt>IP</dt><dd>${escapeHtml(detail.ip_address || '—')}</dd>
                </dl>
                <dl>
                    <dt>User-Agent</dt><dd style="font-size:.78rem">${escapeHtml(detail.user_agent || '—')}</dd>
                </dl>
            `;
            const changes = detail.changes || {};
            const keys = Object.keys(changes);
            if (!keys.length) {
                modalDiff.innerHTML = '<p style="color:var(--au-muted)">Без изменений полей.</p>';
            } else {
                modalDiff.innerHTML = keys.map((k) => {
                    const v = changes[k] || {};
                    const b = v.before;
                    const a = v.after;
                    return `
                        <div class="audit-diff-row">
                            <span class="audit-diff-field">${escapeHtml(k)}</span>
                            <span class="audit-diff-before">${escapeHtml(b === null || b === undefined ? '—' : String(b))}</span>
                            <span class="audit-diff-after">${escapeHtml(a === null || a === undefined ? '—' : String(a))}</span>
                        </div>
                    `;
                }).join('');
            }
            modal.hidden = false;
            modal.setAttribute('aria-hidden', 'false');
        }

        function closeModal() {
            modal.hidden = true;
            modal.setAttribute('aria-hidden', 'true');
        }

        modalCloseEls.forEach((el) => el.addEventListener('click', closeModal));
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !modal.hidden) closeModal();
        });

        timelineEl.addEventListener('click', async (e) => {
            const item = e.target.closest('.audit-item');
            if (!item) return;
            const id = item.dataset.id;
            try {
                const res = await fetch(cfg.detailUrl.replace('/0/', `/${id}/`));
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const data = await res.json();
                openModal(item, data);
            } catch (err) {
                console.error(err);
            }
        });

        // --- initial ------------------------------------------------------
        loadFilterLists();
        load();
        fetchTodayCount();
    });
})();
