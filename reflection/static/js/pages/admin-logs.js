/* admin-logs.js — терминал системных логов.
 *
 * Возможности:
 *  - чтение лог-файла за выбранную дату (media/logs/YYYY-MM/DD.log);
 *  - фильтр по уровню (ALL/INFO/WARN/ERROR/DEBUG);
 *  - фильтр по пользователю (список подтягивается с сервера);
 *  - фильтр по времени (HH:MM от-до);
 *  - текстовый поиск с подсветкой;
 *  - по умолчанию — последние 100 строк, кнопка "показать всё" раскрывает полный список;
 *  - LIVE-режим активен только когда выбран сегодняшний день;
 *  - очистка и скачивание привязаны к выбранной дате.
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const root = document.getElementById('admin-logs-root');
        if (!root) return;

        const cfg = {
            streamUrl: root.dataset.streamUrl,
            datesUrl: root.dataset.datesUrl,
            usersUrl: root.dataset.usersUrl,
            clearUrl: root.dataset.clearUrl,
            downloadUrl: root.dataset.downloadUrl,
            today: root.dataset.today,
        };

        const POLL_MS = 2000;

        const body = document.getElementById('logs-body');
        const meta = document.getElementById('logs-meta');
        const fileTitle = document.getElementById('term-file-title');
        const countEl = document.getElementById('logs-count');
        const totalInline = document.getElementById('logs-total-inline');
        const showAllBtn = document.getElementById('logs-show-all');
        const statusDot = document.getElementById('logs-status-dot');
        const statusText = document.getElementById('logs-status-text');

        const liveBtn = document.getElementById('logs-live-btn');
        const refreshBtn = document.getElementById('logs-refresh-btn');
        const downloadLink = document.getElementById('logs-download-link');
        const confirmClearBtn = document.getElementById('logs-confirm-clear');
        const clearDateEl = document.getElementById('logs-clear-date');

        const levelButtons = document.querySelectorAll('.logs-level-btn');
        const searchInput = document.getElementById('logs-search-input');
        const dateInput = document.getElementById('logs-date');
        const userInput = document.getElementById('logs-user');
        const userClearBtn = document.getElementById('logs-user-clear');
        const userList = document.getElementById('logs-user-list');
        const userCombobox = userInput.closest('.logs-combobox');
        const fromTimeInput = document.getElementById('logs-from-time');
        const toTimeInput = document.getElementById('logs-to-time');
        const resetBtn = document.getElementById('logs-reset-filters');

        let recentUsers = [];
        let userDebounce = null;

        const state = {
            level: 'ALL',
            query: '',
            date: cfg.today,
            user: '',
            fromTime: '',
            toTime: '',
            tail: true,
            live: true,
            stickToBottom: true,
            timer: null,
            lastSignature: null,
        };

        // ---------- helpers ----------

        function getCsrfToken() {
            const el = document.querySelector('input[name="csrfmiddlewaretoken"]');
            if (el) return el.value;
            const m = document.cookie.match(/csrftoken=([^;]+)/);
            return m ? m[1] : '';
        }

        function escapeHtml(str) {
            return String(str)
                .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        }

        function highlight(str, query) {
            if (!query) return escapeHtml(str);
            const safe = escapeHtml(str);
            const q = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            return safe.replace(new RegExp(q, 'gi'), (m) => `<mark>${m}</mark>`);
        }

        function ruEnd(n, forms) {
            n = Math.abs(n) % 100;
            const n1 = n % 10;
            if (n > 10 && n < 20) return forms[2];
            if (n1 > 1 && n1 < 5) return forms[1];
            if (n1 === 1) return forms[0];
            return forms[2];
        }

        function setStatus(kind, text) {
            statusDot.className = 'dot ' + kind;
            statusText.textContent = text;
        }

        function scrollToBottomIfNeeded() {
            if (state.stickToBottom) body.scrollTop = body.scrollHeight;
        }

        function computeSignature(data) {
            const last = data.lines.length ? data.lines[data.lines.length - 1] : null;
            const key = last ? `${last.ts}|${last.message}` : '—';
            return `${data.date}|${state.tail ? 't' : 'a'}|${data.returned}|${data.total}|${key}`;
        }

        function renderLines(lines) {
            if (!lines || lines.length === 0) {
                body.innerHTML = `
                    <div class="logs-empty">
                        <i class="bi bi-inbox"></i> Нет записей под выбранные фильтры.
                        <span class="term-cursor" aria-hidden="true"></span>
                    </div>`;
                return;
            }

            const frag = document.createDocumentFragment();
            for (const p of lines) {
                const el = document.createElement('div');
                el.className = 'log-line';
                el.setAttribute('data-level', p.level || 'RAW');
                el.innerHTML = `
                    <span class="log-line-ts">${escapeHtml(p.ts || '')}</span>
                    <span class="log-line-level">${escapeHtml(p.level || 'RAW')}</span>
                    <span class="log-line-source">${highlight(p.source || '', state.query)}</span>
                    <span class="log-line-msg">${highlight(p.message || '', state.query)}</span>
                `;
                frag.appendChild(el);
            }
            body.innerHTML = '';
            body.appendChild(frag);

            const cursor = document.createElement('span');
            cursor.className = 'term-cursor';
            cursor.setAttribute('aria-hidden', 'true');
            cursor.style.marginLeft = '1rem';
            body.appendChild(cursor);
        }

        function updateDownloadLink() {
            if (!downloadLink || !cfg.downloadUrl) return;
            const url = new URL(cfg.downloadUrl, window.location.origin);
            url.searchParams.set('date', state.date);
            downloadLink.href = url.toString();
        }

        function updateFileTitle() {
            const [y, m, d] = state.date.split('-');
            fileTitle.textContent = `media/logs/${y}-${m}/${d}.log`;
        }

        function isTodaySelected() {
            return state.date === cfg.today;
        }

        // ---------- core fetch ----------

        async function fetchLogs() {
            if (!cfg.streamUrl) return;
            const url = new URL(cfg.streamUrl, window.location.origin);
            url.searchParams.set('date', state.date);
            url.searchParams.set('level', state.level);
            if (state.query) url.searchParams.set('q', state.query);
            if (state.user) url.searchParams.set('user', state.user);
            if (state.fromTime) url.searchParams.set('from_time', state.fromTime);
            if (state.toTime) url.searchParams.set('to_time', state.toTime);
            url.searchParams.set('tail', state.tail ? 'y' : 'n');

            try {
                setStatus(state.live ? 'on' : 'off', 'Обновление…');
                const res = await fetch(url.toString(), {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    cache: 'no-store',
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err.error || ('HTTP ' + res.status));
                }
                const data = await res.json();
                const sig = computeSignature(data);

                if (sig !== state.lastSignature) {
                    renderLines(data.lines);
                    state.lastSignature = sig;
                    scrollToBottomIfNeeded();
                }

                countEl.textContent = `${data.returned} ${ruEnd(data.returned, ['строка', 'строки', 'строк'])}`;
                if (data.truncated) {
                    totalInline.textContent = `(из ${data.total})`;
                    showAllBtn.hidden = false;
                } else {
                    showAllBtn.hidden = true;
                }

                meta.textContent = data.file_exists
                    ? `date:${data.date} · lvl:${state.level} · ${data.returned}/${data.total}`
                    : `нет файла за ${data.date}`;

                setStatus(state.live ? 'on' : 'off',
                    state.live ? 'LIVE · онлайн' : (isTodaySelected() ? 'Пауза' : 'Архив'));
            } catch (e) {
                setStatus('off', 'Ошибка: ' + e.message);
            }
        }

        function startLive() {
            stopLive();
            state.live = true;
            liveBtn.classList.add('is-live');
            liveBtn.disabled = false;
            state.timer = setInterval(fetchLogs, POLL_MS);
        }

        function stopLive() {
            state.live = false;
            liveBtn.classList.remove('is-live');
            if (state.timer) { clearInterval(state.timer); state.timer = null; }
        }

        function onDateChange() {
            const wasToday = isTodaySelected();
            state.date = dateInput.value || cfg.today;
            state.tail = true;
            state.lastSignature = null;
            updateFileTitle();
            updateDownloadLink();
            if (clearDateEl) clearDateEl.textContent = state.date === cfg.today ? 'сегодня' : state.date;

            if (isTodaySelected()) {
                liveBtn.disabled = false;
                startLive();
            } else {
                stopLive();
                liveBtn.disabled = true;
                setStatus('off', 'Архив');
            }
            fetchLogs();
        }

        // ---------- user combobox ----------

        function updateUserClearBtn() {
            userCombobox.classList.toggle('has-value', userInput.value.trim() !== '');
        }

        function renderUserList(items, query) {
            const head = '<div class="logs-combobox-head">последние 10 в логах</div>';
            if (!items.length) {
                userList.innerHTML = head +
                    `<div class="logs-combobox-empty">${
                        query ? 'Нет совпадений — Enter, чтобы применить как есть'
                              : 'Пока никто не светился'
                    }</div>`;
                return;
            }
            const rows = items.map((u) => `
                <div class="logs-combobox-item" role="option" data-username="${escapeHtml(u.username)}">
                    <span class="user-name">${highlight(u.username, query)}</span>
                    <span class="user-role">${escapeHtml(u.role)}</span>
                </div>
            `).join('');
            userList.innerHTML = head + rows;
        }

        function filterUserList() {
            const q = userInput.value.trim().toLowerCase();
            const filtered = q
                ? recentUsers.filter((u) => u.username.toLowerCase().includes(q))
                : recentUsers;
            renderUserList(filtered, q);
        }

        function openUserList() {
            filterUserList();
            userList.hidden = false;
        }

        function closeUserList() {
            userList.hidden = true;
        }

        async function loadUsers() {
            if (!cfg.usersUrl) return;
            try {
                const url = new URL(cfg.usersUrl, window.location.origin);
                url.searchParams.set('date', state.date);
                const res = await fetch(url.toString(), {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                const data = await res.json();
                recentUsers = data.users || [];
                if (!userList.hidden) filterUserList();
            } catch (_) { /* silent */ }
        }

        function applyUserFilter(value) {
            state.user = (value || '').trim();
            state.lastSignature = null;
            updateUserClearBtn();
            fetchLogs();
        }

        // ---------- events ----------

        levelButtons.forEach((btn) => {
            btn.addEventListener('click', () => {
                levelButtons.forEach((b) => b.classList.remove('active'));
                btn.classList.add('active');
                state.level = btn.dataset.level || 'ALL';
                state.lastSignature = null;
                fetchLogs();
            });
        });

        let searchDebounce = null;
        searchInput.addEventListener('input', () => {
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(() => {
                state.query = searchInput.value.trim();
                state.lastSignature = null;
                fetchLogs();
            }, 250);
        });

        dateInput.addEventListener('change', () => {
            onDateChange();
            loadUsers();
        });

        userInput.addEventListener('focus', () => {
            openUserList();
            loadUsers();
        });
        userInput.addEventListener('input', () => {
            updateUserClearBtn();
            filterUserList();
            userList.hidden = false;
            clearTimeout(userDebounce);
            userDebounce = setTimeout(() => applyUserFilter(userInput.value), 350);
        });
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                closeUserList();
                clearTimeout(userDebounce);
                applyUserFilter(userInput.value);
            } else if (e.key === 'Escape') {
                closeUserList();
                userInput.blur();
            }
        });
        userInput.addEventListener('blur', () => {
            setTimeout(closeUserList, 150);
        });
        userList.addEventListener('mousedown', (e) => {
            const item = e.target.closest('.logs-combobox-item');
            if (!item) return;
            e.preventDefault();
            userInput.value = item.dataset.username;
            closeUserList();
            clearTimeout(userDebounce);
            applyUserFilter(item.dataset.username);
        });
        userClearBtn.addEventListener('click', (e) => {
            e.preventDefault();
            userInput.value = '';
            updateUserClearBtn();
            closeUserList();
            clearTimeout(userDebounce);
            applyUserFilter('');
            userInput.focus();
        });

        fromTimeInput.addEventListener('change', () => {
            state.fromTime = fromTimeInput.value;
            state.lastSignature = null;
            fetchLogs();
        });
        toTimeInput.addEventListener('change', () => {
            state.toTime = toTimeInput.value;
            state.lastSignature = null;
            fetchLogs();
        });

        resetBtn.addEventListener('click', () => {
            state.level = 'ALL';
            state.query = '';
            state.user = '';
            state.fromTime = '';
            state.toTime = '';
            state.tail = true;
            levelButtons.forEach((b) => b.classList.toggle('active', b.dataset.level === 'ALL'));
            searchInput.value = '';
            userInput.value = '';
            updateUserClearBtn();
            fromTimeInput.value = '';
            toTimeInput.value = '';
            state.lastSignature = null;
            fetchLogs();
        });

        liveBtn.addEventListener('click', () => {
            if (!isTodaySelected()) return;
            if (state.live) stopLive();
            else startLive();
            setStatus(state.live ? 'on' : 'off', state.live ? 'LIVE · онлайн' : 'Пауза');
        });

        refreshBtn.addEventListener('click', () => {
            state.lastSignature = null;
            fetchLogs();
        });

        showAllBtn.addEventListener('click', () => {
            state.tail = false;
            state.lastSignature = null;
            fetchLogs();
        });

        body.addEventListener('scroll', () => {
            const distanceFromBottom = body.scrollHeight - (body.scrollTop + body.clientHeight);
            state.stickToBottom = distanceFromBottom < 40;
        });

        if (confirmClearBtn) {
            confirmClearBtn.addEventListener('click', async () => {
                confirmClearBtn.disabled = true;
                try {
                    const form = new FormData();
                    form.append('date', state.date);
                    const res = await fetch(cfg.clearUrl, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCsrfToken(),
                            'X-Requested-With': 'XMLHttpRequest',
                        },
                        body: form,
                    });
                    const data = await res.json();
                    if (res.ok && data.status === 'success') {
                        const modalEl = document.getElementById('logsClearModal');
                        const modal = bootstrap.Modal.getInstance(modalEl);
                        if (modal) modal.hide();
                        state.lastSignature = null;
                        await fetchLogs();
                        state.stickToBottom = true;
                        scrollToBottomIfNeeded();
                    } else {
                        alert(data.message || 'Не удалось очистить лог.');
                    }
                } catch (e) {
                    alert('Ошибка: ' + e.message);
                } finally {
                    confirmClearBtn.disabled = false;
                }
            });
        }

        // ---------- init ----------

        updateFileTitle();
        updateDownloadLink();
        loadUsers();
        fetchLogs().then(() => scrollToBottomIfNeeded());
        startLive();
    });
})();
