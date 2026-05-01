/* admin-stats.js — дашборд статистики админ-панели.
 * Использует Chart.js (self-hosted vendor) для 7 разных графиков:
 *  1. Линия с двумя датасетами (регистрации + записи за период)
 *  2. Donut — распределение пользователей по ролям
 *  3. Горизонтальный bar — топ услуг
 *  4. Bar — распределение оценок отзывов
 *  5. Polar area — записи по дню недели
 *  6. Bar — записи по часам суток
 *  7. Area-line — дневная выручка
 * Плюс список топ-клиентов.
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const root = document.getElementById('admin-stats-root');
        if (!root || typeof Chart === 'undefined') return;

        const cfg = { dataUrl: root.dataset.dataUrl, insightsUrl: root.dataset.insightsUrl };
        const rangeBtns = document.querySelectorAll('.stats-range-btn');
        const statusDot = document.getElementById('stats-status-dot');
        const statusText = document.getElementById('stats-status-text');

        const state = { days: 30 };
        const charts = {};

        const insightsBtn = document.getElementById('stats-insights-btn');
        const insightsRefreshBtn = document.getElementById('stats-insights-refresh-btn');
        const insightsStatus = document.getElementById('stats-insights-status');
        const insightsBody = document.getElementById('stats-insights-body');
        const insightsSummary = document.getElementById('stats-insights-summary');
        const insightsChanges = document.getElementById('stats-insights-changes');
        const insightsAnomalies = document.getElementById('stats-insights-anomalies');
        const insightsRecs = document.getElementById('stats-insights-recommendations');
        const insightsProgress = document.getElementById('stats-insights-progress');
        const insightsProgressBar = document.getElementById('stats-insights-progress-bar');

        // ---------- Chart.js defaults ----------
        Chart.defaults.font.family = "'Montserrat', system-ui, sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.color = '#627066';
        Chart.defaults.plugins.legend.labels.boxWidth = 12;
        Chart.defaults.plugins.legend.labels.boxHeight = 12;
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(44,62,53,0.95)';
        Chart.defaults.plugins.tooltip.titleFont = { weight: '700' };
        Chart.defaults.plugins.tooltip.padding = 10;
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
        Chart.defaults.plugins.tooltip.displayColors = true;
        Chart.defaults.plugins.tooltip.borderWidth = 0;

        // ---------- Палитра ----------
        const palette = {
            primary: '#4a7c59',
            primary2: '#8fc0a9',
            accent: '#5ec482',
            gold: '#d4a464',
            coral: '#c96b6b',
            sky: '#6fa8c4',
            plum: '#9a7cc4',
            sand: '#bf9a6a',
        };
        const cycle = [
            palette.primary, palette.accent, palette.gold, palette.sky,
            palette.plum, palette.sand, palette.coral, palette.primary2,
        ];

        // ---------- Helpers ----------
        function setStatus(kind, text) {
            statusDot.className = 'dot ' + kind;
            statusText.textContent = text;
        }

        function short(num) {
            if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M';
            if (num >= 1_000) return (num / 1_000).toFixed(1) + 'k';
            return Math.round(num).toString();
        }

        function fmtMoney(num) {
            return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(Math.round(num || 0));
        }

        function formatDateLabel(iso) {
            // '2026-04-22' → '22 апр'
            const months = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];
            const parts = iso.split('-');
            if (parts.length !== 3) return iso;
            return `${parseInt(parts[2], 10)} ${months[parseInt(parts[1], 10) - 1] || ''}`;
        }

        function gradientFor(ctx, color) {
            const chart = ctx.chart;
            const { ctx: c, chartArea } = chart;
            if (!chartArea) return color;
            const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
            g.addColorStop(0, color + 'CC');
            g.addColorStop(1, color + '10');
            return g;
        }

        function destroy(key) {
            if (charts[key]) { charts[key].destroy(); delete charts[key]; }
        }

        // ---------- Рендеры ----------

        function renderActivityChart(labels, signups, bookings) {
            destroy('activity');
            const el = document.getElementById('chart-activity');
            if (!el) return;
            charts.activity = new Chart(el, {
                type: 'line',
                data: {
                    labels: labels.map(formatDateLabel),
                    datasets: [
                        {
                            label: 'Регистрации',
                            data: signups,
                            borderColor: palette.primary,
                            backgroundColor: (ctx) => gradientFor(ctx, palette.primary),
                            borderWidth: 2.5,
                            tension: 0.35,
                            pointRadius: 0,
                            pointHoverRadius: 5,
                            fill: true,
                        },
                        {
                            label: 'Записи',
                            data: bookings,
                            borderColor: palette.gold,
                            backgroundColor: (ctx) => gradientFor(ctx, palette.gold),
                            borderWidth: 2.5,
                            tension: 0.35,
                            pointRadius: 0,
                            pointHoverRadius: 5,
                            fill: true,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: { legend: { position: 'top', align: 'end' } },
                    scales: {
                        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 8 } },
                        y: { beginAtZero: true, grid: { color: 'rgba(74,124,89,0.08)' }, ticks: { precision: 0 } },
                    },
                },
            });
        }

        function renderRolesChart(byRole) {
            destroy('roles');
            const el = document.getElementById('chart-roles');
            if (!el) return;
            charts.roles = new Chart(el, {
                type: 'doughnut',
                data: {
                    labels: ['Пользователи', 'Модераторы', 'Админы'],
                    datasets: [{
                        data: [byRole.user || 0, byRole.moderator || 0, byRole.admin || 0],
                        backgroundColor: [palette.primary, palette.gold, palette.coral],
                        borderColor: '#fff',
                        borderWidth: 3,
                        hoverOffset: 8,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '62%',
                    plugins: {
                        legend: { position: 'bottom' },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `${ctx.label}: ${ctx.formattedValue}`,
                            },
                        },
                    },
                },
            });
        }

        function renderTopServices(services) {
            destroy('topServices');
            const el = document.getElementById('chart-top-services');
            if (!el) return;
            if (!services.length) {
                charts.topServices = new Chart(el, emptyChart('Нет данных'));
                return;
            }
            charts.topServices = new Chart(el, {
                type: 'bar',
                data: {
                    labels: services.map(s => s.name),
                    datasets: [{
                        label: 'Записей',
                        data: services.map(s => s.c),
                        backgroundColor: services.map((_, i) => cycle[i % cycle.length] + 'CC'),
                        borderColor: services.map((_, i) => cycle[i % cycle.length]),
                        borderWidth: 1,
                        borderRadius: 8,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { beginAtZero: true, grid: { color: 'rgba(74,124,89,0.08)' }, ticks: { precision: 0 } },
                        y: { grid: { display: false }, ticks: { autoSkip: false } },
                    },
                },
            });
        }

        function renderRatings(counts) {
            destroy('ratings');
            const el = document.getElementById('chart-ratings');
            if (!el) return;
            charts.ratings = new Chart(el, {
                type: 'bar',
                data: {
                    labels: ['1★', '2★', '3★', '4★', '5★'],
                    datasets: [{
                        label: 'Отзывов',
                        data: counts,
                        backgroundColor: [
                            palette.coral + 'D0',
                            '#d89a6a' + 'D0',
                            palette.gold + 'D0',
                            palette.accent + 'D0',
                            palette.primary + 'D0',
                        ],
                        borderRadius: 10,
                        borderSkipped: false,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false } },
                        y: { beginAtZero: true, grid: { color: 'rgba(74,124,89,0.08)' }, ticks: { precision: 0 } },
                    },
                },
            });
        }

        function renderWeekday(counts) {
            destroy('weekday');
            const el = document.getElementById('chart-weekday');
            if (!el) return;
            charts.weekday = new Chart(el, {
                type: 'polarArea',
                data: {
                    labels: ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
                    datasets: [{
                        data: counts,
                        backgroundColor: [
                            palette.primary + 'B0', palette.accent + 'B0',
                            palette.primary2 + 'B0', palette.gold + 'B0',
                            palette.sand + 'B0', palette.plum + 'B0',
                            palette.sky + 'B0',
                        ],
                        borderColor: '#fff',
                        borderWidth: 2,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'right' } },
                    scales: {
                        r: {
                            beginAtZero: true,
                            ticks: { display: false, precision: 0 },
                            grid: { color: 'rgba(74,124,89,0.12)' },
                            angleLines: { color: 'rgba(74,124,89,0.15)' },
                        },
                    },
                },
            });
        }

        function renderHours(counts) {
            destroy('hours');
            const el = document.getElementById('chart-hours');
            if (!el) return;
            charts.hours = new Chart(el, {
                type: 'bar',
                data: {
                    labels: Array.from({ length: 24 }, (_, i) => `${i}`),
                    datasets: [{
                        label: 'Записей',
                        data: counts,
                        backgroundColor: counts.map((v, i) => {
                            const max = Math.max(...counts) || 1;
                            const t = v / max;
                            const h = 150 - 20 * t;
                            const s = 30 + 40 * t;
                            const l = 60 - 18 * t;
                            return `hsl(${h} ${s}% ${l}% / 0.8)`;
                        }),
                        borderRadius: 4,
                        borderSkipped: false,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { callbacks: { title: (tt) => `${tt[0].label}:00 — ${tt[0].label}:59` } },
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { autoSkip: false, font: { size: 10 } } },
                        y: { beginAtZero: true, grid: { color: 'rgba(74,124,89,0.08)' }, ticks: { precision: 0 } },
                    },
                },
            });
        }

        function renderRevenue(labels, values) {
            destroy('revenue');
            const el = document.getElementById('chart-revenue');
            if (!el) return;
            charts.revenue = new Chart(el, {
                type: 'line',
                data: {
                    labels: labels.map(formatDateLabel),
                    datasets: [{
                        label: 'Оборот, ₽',
                        data: values,
                        borderColor: palette.primary,
                        backgroundColor: (ctx) => gradientFor(ctx, palette.accent),
                        borderWidth: 2.5,
                        tension: 0.35,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        fill: true,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { callbacks: { label: (ctx) => `₽ ${fmtMoney(ctx.parsed.y)}` } },
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 8 } },
                        y: { beginAtZero: true, grid: { color: 'rgba(74,124,89,0.08)' }, ticks: { callback: (v) => short(v) + ' ₽' } },
                    },
                },
            });
        }

        function renderTopClients(clients) {
            const list = document.getElementById('top-clients');
            if (!list) return;
            if (!clients.length) {
                list.innerHTML = '<li class="empty">Записей пока нет</li>';
                return;
            }
            list.innerHTML = clients.map((u) => `
                <li>
                    <span class="client-name">${escapeHtml(u.username)}</span>
                    <span class="client-count">${u.c}</span>
                </li>
            `).join('');
        }

        function emptyChart(message) {
            return {
                type: 'bar',
                data: { labels: [''], datasets: [{ data: [0], backgroundColor: 'transparent' }] },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: false },
                        title: { display: true, text: message, color: '#9aa39c', font: { size: 14 } },
                    },
                    scales: { x: { display: false }, y: { display: false } },
                },
            };
        }

        // ---------- KPI ----------
        function updateKpi(kpi) {
            const set = (sel, val) => {
                const el = root.querySelector(`[data-kpi="${sel}"]`);
                if (el) el.textContent = val;
            };
            set('total_users', kpi.total_users);
            set('users_user', kpi.users_by_role.user);
            set('users_moderator', kpi.users_by_role.moderator);
            set('users_admin', kpi.users_by_role.admin);
            set('active_services', kpi.active_services);
            set('total_services', kpi.total_services);
            set('total_bookings', kpi.total_bookings);
            set('bookings_in_period', kpi.bookings_in_period);
            set('avg_rating', kpi.avg_rating != null ? kpi.avg_rating.toFixed(2) : '—');
            set('total_reviews', kpi.total_reviews);
            set('total_revenue', fmtMoney(kpi.total_revenue));
        }

        // ---------- Fetch ----------
        async function load() {
            setStatus('on', 'Загрузка…');
            const url = new URL(cfg.dataUrl, window.location.origin);
            url.searchParams.set('days', state.days);
            try {
                const res = await fetch(url.toString(), {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    cache: 'no-store',
                });
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const data = await res.json();
                updateKpi(data.kpi);
                renderActivityChart(data.series.labels, data.series.signups, data.series.bookings);
                renderRolesChart(data.kpi.users_by_role);
                renderTopServices(data.top_services || []);
                renderRatings(data.rating_counts || [0,0,0,0,0]);
                renderWeekday(data.weekday_counts || [0,0,0,0,0,0,0]);
                renderHours(data.hour_counts || Array(24).fill(0));
                renderRevenue(data.series.labels, data.series.revenue || []);
                renderTopClients(data.top_clients || []);
                setStatus('on', `Обновлено • ${new Date().toLocaleTimeString('ru-RU')} • за ${data.days} дн.`);
            } catch (e) {
                setStatus('err', 'Ошибка: ' + e.message);
            }
        }

        function setInsightsStatus(text, kind) {
            if (!insightsStatus) return;
            insightsStatus.textContent = text;
            insightsStatus.dataset.kind = kind || '';
        }

        let insightsTicker = null;
        function startInsightsTicker() {
            const labels = [
                'Собираю статистику…',
                'Формирую промпт для модели…',
                'Отправляю данные в нейросеть…',
                'Модель анализирует метрики…',
                'Почти готово…',
            ];
            let i = 0;
            if (insightsProgress) insightsProgress.hidden = false;
            if (insightsProgressBar) insightsProgressBar.style.animationPlayState = 'running';
            setInsightsStatus(labels[0], 'loading');
            insightsTicker = window.setInterval(() => {
                i = (i + 1) % labels.length;
                setInsightsStatus(labels[i], 'loading');
            }, 1300);
        }

        function stopInsightsTicker() {
            if (insightsTicker) {
                window.clearInterval(insightsTicker);
                insightsTicker = null;
            }
            if (insightsProgress) insightsProgress.hidden = true;
            if (insightsProgressBar) insightsProgressBar.style.animationPlayState = 'paused';
        }

        function renderInsightsList(ul, items, emptyText) {
            if (!ul) return;
            if (!items || !items.length) {
                ul.innerHTML = `<li>${escapeHtml(emptyText || '—')}</li>`;
                return;
            }
            ul.innerHTML = items.map((t) => `<li>${escapeHtml(t)}</li>`).join('');
        }

        function normalizeChangeItems(changes) {
            if (!Array.isArray(changes)) return [];
            return changes
                .map((c) => (c && typeof c === 'object' ? c.text : c))
                .filter((t) => typeof t === 'string' && t.trim().length);
        }

        async function loadInsights(force) {
            if (!cfg.insightsUrl || !insightsBtn || !insightsStatus) return;
            insightsBtn.disabled = true;
            if (insightsRefreshBtn) insightsRefreshBtn.disabled = true;
            startInsightsTicker();

            const url = new URL(cfg.insightsUrl, window.location.origin);
            url.searchParams.set('days', state.days);
            if (force) url.searchParams.set('force', '1');

            try {
                const res = await fetch(url.toString(), {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    cache: 'no-store',
                });
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const data = await res.json();
                if (!data || data.status !== 'success') throw new Error('Bad response');

                const ins = data.insights || {};
                if (insightsSummary) insightsSummary.textContent = ins.summary || '';
                renderInsightsList(insightsChanges, normalizeChangeItems(ins.changes), 'Пока без выраженных изменений.');
                renderInsightsList(insightsAnomalies, ins.anomalies || [], 'Аномалий не обнаружено.');
                renderInsightsList(insightsRecs, ins.recommendations || [], 'Рекомендаций пока нет.');

                if (insightsBody) insightsBody.hidden = false;
                if (insightsRefreshBtn) insightsRefreshBtn.hidden = false;

                const when = data.generated_at ? new Date(data.generated_at).toLocaleTimeString('ru-RU') : new Date().toLocaleTimeString('ru-RU');
                const cached = data.cached ? 'кэш' : 'новое';
                const mode = data.mode || '';
                const elapsed = data.meta && data.meta.elapsed_ms != null ? `${data.meta.elapsed_ms}ms` : '';
                stopInsightsTicker();
                setInsightsStatus(`Готово • ${cached} • ${mode} • ${elapsed} • ${when}`, 'ok');
            } catch (e) {
                stopInsightsTicker();
                setInsightsStatus('Ошибка инсайтов: ' + e.message, 'err');
            } finally {
                insightsBtn.disabled = false;
                if (insightsRefreshBtn) insightsRefreshBtn.disabled = false;
            }
        }

        // ---------- Events ----------
        rangeBtns.forEach((btn) => {
            btn.addEventListener('click', () => {
                rangeBtns.forEach((b) => b.classList.remove('active'));
                btn.classList.add('active');
                state.days = parseInt(btn.dataset.days, 10) || 30;
                load();
                if (insightsBody) insightsBody.hidden = true;
                if (insightsRefreshBtn) insightsRefreshBtn.hidden = true;
                stopInsightsTicker();
                setInsightsStatus('Период изменён. Нажмите «Сгенерировать», чтобы обновить инсайты.', 'idle');
            });
        });

        if (insightsBtn) {
            insightsBtn.addEventListener('click', () => loadInsights(false));
        }
        if (insightsRefreshBtn) {
            insightsRefreshBtn.addEventListener('click', () => loadInsights(true));
        }

        function escapeHtml(s) {
            return String(s)
                .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
                .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
        }

        load();
    });
})();
