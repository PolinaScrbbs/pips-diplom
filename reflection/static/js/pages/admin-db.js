/*
 * admin-db.js
 *
 * DB Inspector:
 *   - ERD: SVG-схема в стиле pgAdmin (draggable узлы, pan/zoom, связи-линии,
 *     side-panel с деталями таблицы). Pure vanilla, без внешних графовых
 *     либ.
 *   - Queries: инкрементальный prepend, event delegation, CSS-фильтры,
 *     throttle-чарт, pause при скрытой вкладке.
 */
(function () {
    'use strict';

    const SVG_NS = 'http://www.w3.org/2000/svg';

    document.addEventListener('DOMContentLoaded', function () {
        const root = document.getElementById('admin-db-root');
        if (!root) return;

        const cfg = {
            schemaUrl: root.dataset.schemaUrl,
            queriesUrl: root.dataset.queriesUrl,
            clearUrl: root.dataset.clearUrl,
        };

        const csrftoken = (function () {
            const input = document.querySelector('input[name=csrfmiddlewaretoken]');
            if (input) return input.value;
            const m = document.cookie.match(/csrftoken=([^;]+)/);
            return m ? m[1] : '';
        })();

        function $(sel, ctx) { return (ctx || root).querySelector(sel); }
        function $$(sel, ctx) { return Array.from((ctx || root).querySelectorAll(sel)); }
        function el(tag, attrs, children) {
            const e = document.createElement(tag);
            if (attrs) for (const k in attrs) {
                if (k === 'class') e.className = attrs[k];
                else if (k === 'text') e.textContent = attrs[k];
                else if (k === 'html') e.innerHTML = attrs[k];
                else e.setAttribute(k, attrs[k]);
            }
            if (children) children.forEach((c) => c && e.appendChild(c));
            return e;
        }
        function svgEl(tag, attrs) {
            const e = document.createElementNS(SVG_NS, tag);
            if (attrs) for (const k in attrs) e.setAttribute(k, attrs[k]);
            return e;
        }
        function escapeHtml(s) {
            return String(s == null ? '' : s)
                .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        }
        function num(v) {
            if (v == null) return '—';
            try { return new Intl.NumberFormat('ru-RU').format(v); }
            catch (e) { return String(v); }
        }

        // ==============================================================
        // Tabs
        // ==============================================================
        const tabs = $$('.db-tab');
        const panels = $$('.db-tab-panel');
        let activeTab = 'schema';
        tabs.forEach((tab) => {
            tab.addEventListener('click', () => {
                activeTab = tab.dataset.tab;
                tabs.forEach((t) => {
                    const active = t === tab;
                    t.classList.toggle('active', active);
                    t.setAttribute('aria-selected', active ? 'true' : 'false');
                });
                panels.forEach((p) => {
                    const active = p.dataset.panel === activeTab;
                    p.classList.toggle('active', active);
                    p.hidden = !active;
                });
                // «Долить» список запросов сразу при переключении на вкладку
                if (activeTab === 'queries') pollQueries(false);
                // ERD — начальный фокус после первого показа, если ещё не делали
                if (activeTab === 'schema' && erd.needsFocus) {
                    erd.needsFocus();
                    erd.needsFocus = null;
                }
            });
        });

        // ==============================================================
        // ERD renderer
        // ==============================================================
        const erdWrap = $('[data-role="erd-wrap"]');
        const erdCanvas = $('[data-role="erd-canvas"]');
        const erdSvg = $('[data-role="erd-svg"]');
        const erdViewport = $('[data-role="erd-viewport"]');
        const erdEdges = $('[data-role="erd-edges"]');
        const erdNodesG = $('[data-role="erd-nodes"]');
        const erdEmpty = $('[data-role="erd-empty"]');
        const erdHudZoom = $('[data-role="erd-zoom"]');
        const erdDetails = $('[data-role="erd-details"]');
        const appFilter = $('[data-role="app-filter"]');
        const schemaSearch = $('[data-role="schema-search"]');

        erdEdges.classList.add('erd-edges-g');

        // Geometry constants — узлы крупные и читаемые, как в pgAdmin
        const NODE_WIDTH = 320;
        const HEAD_H = 42;
        const SUB_H = 24;
        const FIELD_H = 30;
        const NODE_PAD_BOTTOM = 10;
        const MAX_FIELDS_PREVIEW = 12;

        function nodeHeight(t) {
            const shown = Math.min(t.fields.length, MAX_FIELDS_PREVIEW);
            const more = t.fields.length > MAX_FIELDS_PREVIEW ? 24 : 0;
            return HEAD_H + SUB_H + 6 + shown * FIELD_H + more + NODE_PAD_BOTTOM;
        }

        const erd = {
            tables: [],         // array of table info
            relations: [],
            byLabel: new Map(), // label → node state
            // viewport state
            scale: 1, tx: 0, ty: 0,
            minScale: 0.3, maxScale: 2.2,
            selected: null,
            activeApp: 'ALL',
            searchQuery: '',
            needsFit: false,

            applyTransform() {
                erdViewport.setAttribute('transform', `translate(${this.tx},${this.ty}) scale(${this.scale})`);
                if (erdHudZoom) erdHudZoom.textContent = Math.round(this.scale * 100) + '%';
            },

            /**
             * Force-directed layout: узлы отталкиваются друг от друга
             * (кулоновская сила), связи работают как пружины.
             * Для 10–30 таблиц сходится за ~400 итераций мгновенно.
             */
            layout(tables) {
                const n = tables.length;
                if (!n) return;

                // Подготовка узлов: начальное размещение по спирали вокруг центра,
                // группируя по app — это даёт симуляции лучший старт, чем случайный.
                const byApp = new Map();
                tables.forEach((t) => {
                    if (!byApp.has(t.app)) byApp.set(t.app, []);
                    byApp.get(t.app).push(t);
                });
                const apps = Array.from(byApp.keys());
                const nodes = [];
                let i = 0;
                apps.forEach((app, appIdx) => {
                    const groupAngleBase = (appIdx / apps.length) * Math.PI * 2;
                    const groupRadius = 380;
                    const cx = Math.cos(groupAngleBase) * groupRadius;
                    const cy = Math.sin(groupAngleBase) * groupRadius;
                    byApp.get(app).forEach((t, idx) => {
                        const local = idx * 140;
                        const angle = groupAngleBase + idx * 0.6;
                        const state = this.byLabel.get(t.label) || {};
                        state.t = t;
                        state.w = NODE_WIDTH;
                        state.h = nodeHeight(t);
                        state.x = cx + Math.cos(angle) * local;
                        state.y = cy + Math.sin(angle) * local;
                        state.vx = 0;
                        state.vy = 0;
                        state.label = t.label;
                        this.byLabel.set(t.label, state);
                        nodes.push(state);
                        i++;
                    });
                });

                // Связи из relations (двунаправленные — для пружин направление не важно)
                const byLabel = this.byLabel;
                const edges = [];
                this.relations.forEach((r) => {
                    const a = byLabel.get(r.from_model);
                    const b = byLabel.get(r.to_model);
                    if (a && b && a !== b) edges.push({ a, b });
                });

                // Параметры симуляции.
                //   K_REP — сила отталкивания (обратно квадрат расстояния).
                //   IDEAL — желаемая длина пружины (от центра до центра).
                //   K_ATTR — жёсткость пружины связи.
                const IDEAL = 340;
                const K_REP = 180000;
                const K_ATTR = 0.012;
                const DAMPING = 0.82;
                const ITER = 450;

                for (let step = 0; step < ITER; step++) {
                    const cooling = 1 - step / ITER;

                    // Repulsion O(n²) — для 10–30 узлов копейки
                    for (let a = 0; a < nodes.length; a++) {
                        for (let b = a + 1; b < nodes.length; b++) {
                            const na = nodes[a], nb = nodes[b];
                            let dx = nb.x - na.x;
                            let dy = nb.y - na.y;
                            let dist = Math.sqrt(dx * dx + dy * dy);
                            if (dist < 0.5) {
                                dx = Math.random() - 0.5;
                                dy = Math.random() - 0.5;
                                dist = Math.sqrt(dx * dx + dy * dy);
                            }
                            // Считаем минимальное «безопасное» расстояние чтобы
                            // крупные узлы не перекрывались.
                            const minDist = (na.w + nb.w) / 2 + 40;
                            const effDist = Math.max(dist, 1);
                            // Усиливаем отталкивание, если узлы сблизились плотнее minDist
                            const boost = effDist < minDist ? (minDist / effDist) : 1;
                            const force = (K_REP * boost) / (effDist * effDist);
                            const fx = (dx / effDist) * force;
                            const fy = (dy / effDist) * force;
                            na.vx -= fx; na.vy -= fy;
                            nb.vx += fx; nb.vy += fy;
                        }
                    }

                    // Attraction по связям
                    edges.forEach(({ a, b }) => {
                        const dx = b.x - a.x;
                        const dy = b.y - a.y;
                        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                        const target = IDEAL + (a.w + b.w) / 4; // учёт ширины
                        const force = K_ATTR * (dist - target);
                        const fx = (dx / dist) * force;
                        const fy = (dy / dist) * force;
                        a.vx += fx; a.vy += fy;
                        b.vx -= fx; b.vy -= fy;
                    });

                    // Применяем скорость (масштабируем cooling'ом)
                    nodes.forEach((nd) => {
                        nd.x += nd.vx * cooling;
                        nd.y += nd.vy * cooling;
                        nd.vx *= DAMPING;
                        nd.vy *= DAMPING;
                    });
                }

                // Финальный проход: разводим AABB-перекрывающиеся узлы
                for (let pass = 0; pass < 6; pass++) {
                    let moved = false;
                    for (let a = 0; a < nodes.length; a++) {
                        for (let b = a + 1; b < nodes.length; b++) {
                            const na = nodes[a], nb = nodes[b];
                            const overlapX = (na.w + nb.w) / 2 + 24 - Math.abs(nb.x - na.x);
                            const overlapY = (na.h + nb.h) / 2 + 24 - Math.abs(nb.y - na.y);
                            if (overlapX > 0 && overlapY > 0) {
                                moved = true;
                                if (overlapX < overlapY) {
                                    const sign = nb.x > na.x ? 1 : -1;
                                    na.x -= (overlapX / 2) * sign;
                                    nb.x += (overlapX / 2) * sign;
                                } else {
                                    const sign = nb.y > na.y ? 1 : -1;
                                    na.y -= (overlapY / 2) * sign;
                                    nb.y += (overlapY / 2) * sign;
                                }
                            }
                        }
                    }
                    if (!moved) break;
                }

                // Сдвиг в положительные координаты
                let minX = Infinity, minY = Infinity;
                nodes.forEach((nd) => {
                    // Узел рендерится от top-left, так что x/y — это левый верхний угол.
                    // Симулируем мы центры, поэтому сдвинем в угол.
                    nd.x -= nd.w / 2;
                    nd.y -= nd.h / 2;
                    if (nd.x < minX) minX = nd.x;
                    if (nd.y < minY) minY = nd.y;
                });
                const pad = 50;
                nodes.forEach((nd) => {
                    nd.x = nd.x - minX + pad;
                    nd.y = nd.y - minY + pad;
                });
            },

            buildNodes() {
                erdNodesG.innerHTML = '';
                const frag = document.createDocumentFragment();
                this.tables.forEach((t) => {
                    const state = this.byLabel.get(t.label);
                    const g = this.makeNodeEl(t, state);
                    state.el = g;
                    frag.appendChild(g);
                });
                erdNodesG.appendChild(frag);
            },

            makeNodeEl(t, state) {
                const g = svgEl('g', {
                    class: 'erd-node',
                    transform: `translate(${state.x},${state.y})`,
                    'data-label': t.label,
                    'data-app': t.app,
                });
                g.dataset.search = (
                    t.label + ' ' + t.verbose + ' ' + t.verbose_plural + ' ' +
                    t.fields.map((f) => f.name).join(' ')
                ).toLowerCase();

                const fo = svgEl('foreignObject', {
                    x: 0, y: 0, width: NODE_WIDTH, height: state.h,
                });

                const fields = t.fields.slice(0, MAX_FIELDS_PREVIEW);
                const extra = t.fields.length > MAX_FIELDS_PREVIEW
                    ? `<div class="erd-node-more">+${t.fields.length - MAX_FIELDS_PREVIEW} поля</div>`
                    : '';
                fo.innerHTML = `
                    <div xmlns="http://www.w3.org/1999/xhtml" class="erd-node-html">
                        <div class="erd-node-head">
                            <span class="erd-node-title"><i class="bi bi-table"></i>${escapeHtml(t.model)}</span>
                            <span class="erd-node-rows">${t.rows == null ? '—' : num(t.rows)}</span>
                        </div>
                        <div class="erd-node-sub">${escapeHtml(t.app)}.${escapeHtml(t.table)}</div>
                        <div class="erd-node-fields">
                            ${fields.map((f) => this.fieldRow(f)).join('')}
                            ${extra}
                        </div>
                    </div>
                `;
                g.appendChild(fo);
                return g;
            },

            fieldRow(f) {
                const cls = ['erd-node-field'];
                let mark = '';
                if (f.primary_key) { cls.push('is-pk'); mark = '🔑'; }
                else if (f.fk) { cls.push('is-fk'); mark = '→'; }
                else if (f.unique) mark = 'U';
                else if (f.db_index) mark = 'I';
                let typeStr = f.type;
                if (f.max_length) typeStr += `(${f.max_length})`;
                return `
                    <div class="${cls.join(' ')}">
                        <span class="erd-node-field-mark">${mark}</span>
                        <span class="erd-node-field-name">${escapeHtml(f.name)}</span>
                        <span class="erd-node-field-type">${escapeHtml(typeStr)}</span>
                    </div>
                `;
            },

            buildEdges() {
                erdEdges.innerHTML = '';
                this.edges = [];
                const labelSet = new Set(this.tables.map((t) => t.label));
                this.relations.forEach((r) => {
                    if (!labelSet.has(r.from_model) || !labelSet.has(r.to_model)) return;
                    const path = svgEl('path', {
                        class: 'erd-edge' + (r.kind === 'M2M' ? ' m2m' : ''),
                        'data-from': r.from_model,
                        'data-to': r.to_model,
                    });
                    erdEdges.appendChild(path);
                    this.edges.push({ path, r });
                });
                this.redrawEdges();
            },

            redrawEdges() {
                this.edges.forEach(({ path, r }) => {
                    const a = this.byLabel.get(r.from_model);
                    const b = this.byLabel.get(r.to_model);
                    if (!a || !b) return;
                    path.setAttribute('d', cubicPath(a, b));
                });
            },

            // update edges for single node (when dragging)
            redrawEdgesFor(label) {
                this.edges.forEach(({ path, r }) => {
                    if (r.from_model !== label && r.to_model !== label) return;
                    const a = this.byLabel.get(r.from_model);
                    const b = this.byLabel.get(r.to_model);
                    if (a && b) path.setAttribute('d', cubicPath(a, b));
                });
            },

            highlightFor(label) {
                this.edges.forEach(({ path, r }) => {
                    const isMine = r.from_model === label || r.to_model === label;
                    path.classList.toggle('highlight', isMine);
                    path.classList.toggle('dimmed', !isMine);
                });
                this.byLabel.forEach((state, l) => {
                    const involved = l === label ||
                        this.relations.some((r) =>
                            (r.from_model === label && r.to_model === l) ||
                            (r.to_model === label && r.from_model === l));
                    state.el.classList.toggle('dimmed', !involved);
                });
            },

            clearHighlight() {
                this.edges.forEach(({ path }) => {
                    path.classList.remove('highlight', 'dimmed');
                });
                this.byLabel.forEach((state) => state.el.classList.remove('dimmed'));
            },

            fitView() {
                if (!this.tables.length) return;
                const pad = 40;
                let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
                this.byLabel.forEach((s) => {
                    minX = Math.min(minX, s.x);
                    minY = Math.min(minY, s.y);
                    maxX = Math.max(maxX, s.x + s.w);
                    maxY = Math.max(maxY, s.y + s.h);
                });
                const w = erdCanvas.clientWidth || 1000;
                const h = erdCanvas.clientHeight || 600;
                const contentW = maxX - minX + pad * 2;
                const contentH = maxY - minY + pad * 2;
                const scale = Math.min(w / contentW, h / contentH, 1);
                this.scale = Math.max(this.minScale, Math.min(this.maxScale, scale));
                this.tx = (w - contentW * this.scale) / 2 - (minX - pad) * this.scale;
                this.ty = (h - contentH * this.scale) / 2 - (minY - pad) * this.scale;
                this.applyTransform();
            },

            /**
             * Центрирует viewport на конкретной таблице с заданным масштабом.
             * Используется при начальной загрузке: по умолчанию открываем
             * схему на User с масштабом 67% — главная точка входа в модель.
             */
            focusTable(label, scale) {
                const state = this.byLabel.get(label);
                if (!state) { this.fitView(); return; }
                this.scale = Math.max(this.minScale, Math.min(this.maxScale, scale || 0.67));
                const w = erdCanvas.clientWidth || 1000;
                const h = erdCanvas.clientHeight || 600;
                const cx = state.x + state.w / 2;
                const cy = state.y + state.h / 2;
                this.tx = w / 2 - cx * this.scale;
                this.ty = h / 2 - cy * this.scale;
                this.applyTransform();
            },

            zoomAt(factor, cx, cy) {
                const prev = this.scale;
                const next = Math.max(this.minScale, Math.min(this.maxScale, prev * factor));
                const k = next / prev;
                this.tx = cx - (cx - this.tx) * k;
                this.ty = cy - (cy - this.ty) * k;
                this.scale = next;
                this.applyTransform();
            },

            select(label) {
                if (this.selected) {
                    const prev = this.byLabel.get(this.selected);
                    if (prev && prev.el) prev.el.classList.remove('selected');
                }
                this.selected = label;
                if (!label) {
                    erdWrap.classList.remove('with-details');
                    erdDetails.hidden = true;
                    this.clearHighlight();
                    return;
                }
                const state = this.byLabel.get(label);
                if (!state) return;
                state.el.classList.add('selected');
                this.highlightFor(label);
                this.renderDetails(state.t);
                erdWrap.classList.add('with-details');
                erdDetails.hidden = false;
            },

            renderDetails(t) {
                $('[data-role="d-title"]').textContent = t.model;
                $('[data-role="d-sub"]').textContent = `${t.app}.${t.table}`;
                $('[data-role="d-rows"]').textContent = t.rows == null ? '—' : num(t.rows);
                $('[data-role="d-fields"]').textContent = t.field_count;
                $('[data-role="d-managed"]').textContent = t.managed ? 'Да' : 'Нет';

                const flist = $('[data-role="d-fields-list"]');
                flist.innerHTML = t.fields.map((f) => {
                    const badges = [];
                    if (f.primary_key) badges.push('<span class="db-badge-mini db-badge-pk">PK</span>');
                    if (f.fk) badges.push(`<span class="db-badge-mini db-badge-fk" title="${escapeHtml(f.fk)}">FK</span>`);
                    if (f.unique && !f.primary_key) badges.push('<span class="db-badge-mini db-badge-uq">UQ</span>');
                    if (f.db_index && !f.unique && !f.primary_key) badges.push('<span class="db-badge-mini db-badge-ix">IX</span>');
                    if (!f.null && !f.primary_key) badges.push('<span class="db-badge-mini db-badge-nn">NN</span>');
                    let typeStr = f.type + (f.max_length ? `(${f.max_length})` : '');
                    const help = f.help_text ? `<div class="erd-field-help">${escapeHtml(f.help_text)}</div>` : '';
                    return `
                        <li class="erd-field">
                            <span class="erd-field-name">${escapeHtml(f.name)}</span>
                            <span class="erd-badges">
                                <span class="erd-field-type">${escapeHtml(typeStr)}</span>
                                ${badges.join('')}
                            </span>
                            ${help}
                        </li>
                    `;
                }).join('') || '<li class="erd-field"><span class="erd-field-name">—</span></li>';

                const rels = this.relations.filter(
                    (r) => r.from_model === t.label || r.to_model === t.label
                );
                const rlist = $('[data-role="d-rels-list"]');
                if (!rels.length) {
                    rlist.innerHTML = '<li style="color: var(--db-muted); font-size: 0.82rem; padding: 6px 10px;">нет связей</li>';
                } else {
                    rlist.innerHTML = rels.map((r) => {
                        const isIn = r.to_model === t.label;
                        const other = isIn ? r.from_model : r.to_model;
                        const arrow = isIn ? '←' : '→';
                        return `
                            <li class="erd-rel" data-goto="${escapeHtml(other)}" title="Перейти к ${escapeHtml(other)}">
                                <span class="erd-rel-kind ${r.kind}">${r.kind}</span>
                                <span class="erd-rel-field">${escapeHtml(r.field)}</span>
                                <span class="erd-rel-arrow">${arrow}</span>
                                <span class="erd-rel-target">${escapeHtml(other)}</span>
                            </li>
                        `;
                    }).join('');
                }
            },

            applyFilters() {
                const q = this.searchQuery.trim().toLowerCase();
                let visible = 0;
                this.byLabel.forEach((state) => {
                    const appOk = this.activeApp === 'ALL' || state.t.app === this.activeApp;
                    const qOk = !q || state.el.dataset.search.indexOf(q) !== -1;
                    const show = appOk && qOk;
                    state.el.style.display = show ? '' : 'none';
                    if (show) visible++;
                });
                this.edges.forEach(({ path, r }) => {
                    const a = this.byLabel.get(r.from_model);
                    const b = this.byLabel.get(r.to_model);
                    const show = a && b &&
                        a.el.style.display !== 'none' &&
                        b.el.style.display !== 'none';
                    path.style.display = show ? '' : 'none';
                });
            },
        };

        // Cubic bezier edge path — rightmost middle of A → leftmost middle of B
        function cubicPath(a, b) {
            const ax = a.x + a.w, ay = a.y + a.h / 2;
            const bx = b.x, by = b.y + b.h / 2;
            const midX = (ax + bx) / 2;
            // правая→левая если B правее, иначе заход сбоку
            const aDir = bx > ax ? 1 : -1;
            const bDir = -aDir;
            const handle = Math.max(50, Math.abs(bx - ax) / 2);
            const c1x = ax + handle * aDir;
            const c2x = bx + handle * bDir;
            return `M ${ax} ${ay} C ${c1x} ${ay}, ${c2x} ${by}, ${bx} ${by}`;
        }

        // Pan
        let panning = false, panStart = null;
        erdCanvas.addEventListener('mousedown', (e) => {
            // drag по фону (не по узлу)
            if (e.target.closest('.erd-node')) return;
            panning = true;
            panStart = { x: e.clientX - erd.tx, y: e.clientY - erd.ty };
            erdCanvas.classList.add('is-panning');
        });
        window.addEventListener('mousemove', (e) => {
            if (!panning) return;
            erd.tx = e.clientX - panStart.x;
            erd.ty = e.clientY - panStart.y;
            erd.applyTransform();
        });
        window.addEventListener('mouseup', () => {
            panning = false;
            erdCanvas.classList.remove('is-panning');
        });

        // Zoom
        erdCanvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const rect = erdCanvas.getBoundingClientRect();
            const cx = e.clientX - rect.left;
            const cy = e.clientY - rect.top;
            const factor = e.deltaY < 0 ? 1.12 : 0.89;
            erd.zoomAt(factor, cx, cy);
        }, { passive: false });

        $('[data-role="erd-zoom-in"]').addEventListener('click', () => {
            const r = erdCanvas.getBoundingClientRect();
            erd.zoomAt(1.2, r.width / 2, r.height / 2);
        });
        $('[data-role="erd-zoom-out"]').addEventListener('click', () => {
            const r = erdCanvas.getBoundingClientRect();
            erd.zoomAt(1 / 1.2, r.width / 2, r.height / 2);
        });
        $('[data-role="erd-fit"]').addEventListener('click', () => erd.fitView());
        $('[data-role="erd-reset"]').addEventListener('click', () => {
            erd.layout(erd.tables);
            erd.buildNodes();
            attachNodeHandlers();
            erd.buildEdges();
            const pref = erd.tables.find((t) => t.label === 'users.User') ||
                erd.tables.find((t) => t.model === 'User');
            if (pref) erd.focusTable(pref.label, 0.67);
            else erd.fitView();
            erd.select(null);
        });

        // Node drag + click
        let nodeDrag = null;
        function attachNodeHandlers() {
            erdNodesG.querySelectorAll('.erd-node').forEach((g) => {
                g.addEventListener('mousedown', (e) => {
                    e.stopPropagation();
                    const label = g.dataset.label;
                    const state = erd.byLabel.get(label);
                    if (!state) return;
                    nodeDrag = {
                        label, state,
                        startX: e.clientX, startY: e.clientY,
                        origX: state.x, origY: state.y,
                        moved: false,
                    };
                    g.classList.add('dragging');
                });
            });
        }
        window.addEventListener('mousemove', (e) => {
            if (!nodeDrag) return;
            const dx = (e.clientX - nodeDrag.startX) / erd.scale;
            const dy = (e.clientY - nodeDrag.startY) / erd.scale;
            if (Math.abs(dx) + Math.abs(dy) > 3) nodeDrag.moved = true;
            nodeDrag.state.x = nodeDrag.origX + dx;
            nodeDrag.state.y = nodeDrag.origY + dy;
            nodeDrag.state.el.setAttribute('transform', `translate(${nodeDrag.state.x},${nodeDrag.state.y})`);
            erd.redrawEdgesFor(nodeDrag.label);
        });
        window.addEventListener('mouseup', (e) => {
            if (!nodeDrag) return;
            nodeDrag.state.el.classList.remove('dragging');
            const { label, moved } = nodeDrag;
            nodeDrag = null;
            if (!moved) erd.select(label === erd.selected ? null : label);
        });

        // Close details
        $('[data-role="d-close"]').addEventListener('click', () => erd.select(null));
        erdDetails.addEventListener('click', (e) => {
            const rel = e.target.closest('[data-goto]');
            if (rel) erd.select(rel.dataset.goto);
        });

        // Search
        schemaSearch.addEventListener('input', debounce((e) => {
            erd.searchQuery = e.target.value;
            erd.applyFilters();
        }, 120));

        // ==============================================================
        // Schema loader
        // ==============================================================
        async function loadSchema() {
            try {
                const res = await fetch(cfg.schemaUrl);
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const data = await res.json();
                renderSchema(data);
            } catch (err) {
                console.error(err);
                erdEmpty.innerHTML = '<div class="db-schema-placeholder">Ошибка загрузки схемы</div>';
            }
        }

        function renderSchema(data) {
            const { tables, relations, summary } = data;

            // meta
            $('[data-role="engine"]').textContent = summary.engine || '—';
            $('[data-role="database"]').textContent = (summary.database || '—').split('/').pop();
            $('[data-role="kpi-tables"]').textContent = num(summary.table_count);
            $('[data-role="kpi-rows"]').textContent = num(summary.total_rows);
            $('[data-role="kpi-relations"]').textContent = num(summary.relation_count);
            const apps = Array.from(new Set(tables.map((t) => t.app))).sort();
            $('[data-role="kpi-apps"]').textContent = num(apps.length);

            // App filter chips
            appFilter.innerHTML = '';
            const all = document.createElement('button');
            all.type = 'button';
            all.className = 'erd-chip active';
            all.dataset.app = 'ALL';
            all.textContent = 'Все приложения';
            appFilter.appendChild(all);
            apps.forEach((a) => {
                const b = document.createElement('button');
                b.type = 'button';
                b.className = 'erd-chip';
                b.dataset.app = a;
                b.textContent = a;
                appFilter.appendChild(b);
            });
            appFilter.addEventListener('click', (e) => {
                const btn = e.target.closest('.erd-chip');
                if (!btn) return;
                appFilter.querySelectorAll('.erd-chip').forEach((b) => b.classList.toggle('active', b === btn));
                erd.activeApp = btn.dataset.app;
                erd.applyFilters();
            });

            // Render ERD
            erd.tables = tables;
            erd.relations = relations;
            erd.byLabel = new Map();
            erd.layout(tables);
            erd.buildNodes();
            attachNodeHandlers();
            erd.buildEdges();
            erdEmpty.style.display = tables.length ? 'none' : '';

            // Начальный вид: 67% и центр на таблице User (главная точка входа модели).
            // Если User не найден — fallback к fitView.
            const initFocus = () => {
                const pref = tables.find((t) => t.label === 'users.User') ||
                    tables.find((t) => t.model === 'User');
                if (pref) erd.focusTable(pref.label, 0.67);
                else erd.fitView();
            };
            if (activeTab === 'schema') initFocus();
            else erd.needsFocus = initFocus;
        }

        // ==============================================================
        // Queries — OPTIMIZED live log
        // ==============================================================
        const queriesList = $('[data-role="queries-list"]');
        const queriesEmpty = $('[data-role="queries-empty"]');
        const queriesCountBadge = $('[data-role="queries-count"]');
        const queriesSearch = $('[data-role="queries-search"]');
        const pauseBtn = $('[data-role="pause"]');
        const clearBtn = $('[data-role="clear"]');
        const opChips = $$('.db-op-chip');

        const kpi = {
            buffer: $('[data-role="q-buffer"]'),
            avg: $('[data-role="q-avg"]'),
            max: $('[data-role="q-max"]'),
            slow: $('[data-role="q-slow"]'),
        };

        const MAX_DOM = 200;     // максимум DOM-узлов в списке
        const POLL_MS = 3000;    // интервал поллинга
        const CHART_THROTTLE = 1500;

        const qState = {
            paused: false,
            lastId: 0,
            cache: new Map(),    // id → query obj (для модалки)
            searchQuery: '',
            pendingChart: false,
            lastChartAt: 0,
        };

        function formatMs(ms) {
            if (ms == null) return '—';
            if (ms < 1) return ms.toFixed(2) + ' мс';
            if (ms < 100) return ms.toFixed(1) + ' мс';
            return ms.toFixed(0) + ' мс';
        }
        function speedClass(ms) {
            if (ms == null) return '';
            if (ms < 10) return 'is-fast';
            if (ms < 50) return '';
            if (ms < 200) return 'is-mid';
            return 'is-slow';
        }
        function fmtTs(iso) {
            try {
                const d = new Date(iso);
                return d.toLocaleTimeString('ru-RU', { hour12: false }) +
                    '.' + String(d.getMilliseconds()).padStart(3, '0');
            } catch (e) { return iso || ''; }
        }
        function highlightSql(sql) {
            const safe = escapeHtml(sql || '');
            const KW = /\b(SELECT|FROM|WHERE|JOIN|INNER|LEFT|RIGHT|OUTER|ON|AND|OR|NOT|IN|IS|NULL|ORDER BY|GROUP BY|LIMIT|OFFSET|UPDATE|SET|INSERT INTO|VALUES|DELETE|RETURNING|AS|DESC|ASC|DISTINCT|HAVING|UNION|CASE|WHEN|THEN|ELSE|END|LIKE|BETWEEN|EXISTS)\b/gi;
            return safe
                .replace(/'([^']*)'/g, (m) => `<span class="str">${m}</span>`)
                .replace(/"([^"]+)"/g, (m, p1) => `<span class="tbl">"${p1}"</span>`)
                .replace(KW, (m) => `<span class="kw">${m}</span>`)
                .replace(/\b(\d+)\b/g, '<span class="num">$1</span>');
        }

        function buildQueryEl(q) {
            const li = document.createElement('li');
            li.className = 'db-query is-new';
            li.dataset.op = q.op;
            li.dataset.id = q.id;
            const searchBlob = (q.sql + ' ' + (q.path || '') + ' ' + (q.user || '')).toLowerCase();
            li.dataset.search = searchBlob;

            // Пометка для CSS-фильтра поиска: если поиск активен — считаем match сразу
            if (qState.searchQuery && searchBlob.indexOf(qState.searchQuery) !== -1) {
                li.classList.add('is-match');
            }

            const speed = speedClass(q.duration_ms);
            const sqlShort = (q.sql || '').length > 400
                ? q.sql.slice(0, 400) + ' …' : (q.sql || '');
            // SQL — БЕЗ подсветки в списке (подсветка только в модалке).
            // Это самая дорогая операция, убираем её из hot-path.
            li.innerHTML = `
                <div class="db-query-head">
                    <span class="db-query-op">${escapeHtml(q.op)}</span>
                    <span class="db-query-time ${speed}">${formatMs(q.duration_ms)}</span>
                    ${q.user ? `<span class="db-query-user">${escapeHtml(q.user)}</span>` : ''}
                    ${q.path ? `<span class="db-query-path" title="${escapeHtml(q.path)}">${escapeHtml(q.path)}</span>` : ''}
                    <span class="db-query-ts">${escapeHtml(fmtTs(q.ts))}</span>
                </div>
                <pre class="db-query-sql">${escapeHtml(sqlShort)}</pre>
            `;
            // Снимаем is-new через animationend (освобождение GPU)
            li.addEventListener('animationend', () => li.classList.remove('is-new'), { once: true });
            return li;
        }

        // Event delegation (один listener вместо 200)
        queriesList.addEventListener('click', (e) => {
            const li = e.target.closest('.db-query');
            if (!li) return;
            const q = qState.cache.get(Number(li.dataset.id));
            if (q) openModal(q);
        });

        function prependQueries(items) {
            if (!items.length) return;
            const frag = document.createDocumentFragment();
            // items пришли по возрастанию id — в списке сверху должен быть самый свежий,
            // поэтому добавляем в обратном порядке
            for (let i = items.length - 1; i >= 0; i--) {
                const q = items[i];
                qState.cache.set(q.id, q);
                frag.appendChild(buildQueryEl(q));
            }
            queriesList.insertBefore(frag, queriesList.firstChild);

            // Trim overflow
            while (queriesList.children.length > MAX_DOM) {
                const last = queriesList.lastElementChild;
                if (!last) break;
                qState.cache.delete(Number(last.dataset.id));
                queriesList.removeChild(last);
            }
        }

        function applySearchFilter() {
            const q = qState.searchQuery;
            if (!q) {
                queriesList.dataset.hasSearch = '0';
                // удалить is-match у всех (не обязательно — CSS его игнорирует)
                return;
            }
            queriesList.dataset.hasSearch = '1';
            // помечаем matches за один проход, без display-вычислений
            queriesList.querySelectorAll('.db-query').forEach((li) => {
                li.classList.toggle('is-match', li.dataset.search.indexOf(q) !== -1);
            });
        }

        function updateKpi(stats) {
            const hasData = (stats.buffer_size || 0) > 0;
            kpi.buffer.textContent = num(stats.buffer_size);
            // avg/max: показываем число даже когда оно =0 (запросы бывают субмиллисекундные);
            // прочерк — только если буфер пуст.
            kpi.avg.textContent = hasData ? Number(stats.avg_ms || 0).toFixed(2) : '—';
            kpi.max.textContent = hasData ? Number(stats.max_ms || 0).toFixed(2) : '—';
            kpi.slow.textContent = num(stats.slow_count);
            queriesCountBadge.textContent = stats.buffer_size || 0;
            queriesEmpty.hidden = hasData;
        }

        // ---- Chart (throttled) ----
        let chart = null;
        const chartCanvas = $('[data-role="q-chart"]');

        function ensureChart() {
            if (chart || typeof Chart === 'undefined' || !chartCanvas) return chart;
            chart = new Chart(chartCanvas.getContext('2d'), {
                type: 'line',
                data: { labels: [], datasets: [{
                    label: 'мс', data: [],
                    borderColor: '#2f6b3f',
                    backgroundColor: 'rgba(47, 107, 63, 0.14)',
                    borderWidth: 1.4, pointRadius: 0, tension: 0.3, fill: true,
                }] },
                options: {
                    responsive: true, maintainAspectRatio: false, animation: false,
                    layout: { padding: 0 },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            displayColors: false,
                            callbacks: {
                                title: (items) => `#${items[0].label}`,
                                label: (ctx) => `${ctx.parsed.y.toFixed(2)} мс`,
                            },
                        },
                    },
                    scales: {
                        x: { display: false },
                        y: { display: false, beginAtZero: true },
                    },
                },
            });
            return chart;
        }

        function scheduleChartUpdate() {
            const now = Date.now();
            const elapsed = now - qState.lastChartAt;
            if (elapsed >= CHART_THROTTLE) {
                doChartUpdate();
            } else if (!qState.pendingChart) {
                qState.pendingChart = true;
                setTimeout(doChartUpdate, CHART_THROTTLE - elapsed);
            }
        }
        function doChartUpdate() {
            qState.pendingChart = false;
            qState.lastChartAt = Date.now();
            const c = ensureChart();
            if (!c) return;
            // берём последние 100 значений (sparkline — компактно) в хронологическом порядке
            const items = Array.from(qState.cache.values())
                .sort((a, b) => a.id - b.id)
                .slice(-100);
            c.data.labels = items.map((q) => q.id);
            c.data.datasets[0].data = items.map((q) => q.duration_ms);
            c.update('none');
        }

        // ---- polling ----
        let pollTimer = null;
        async function pollQueries(initial) {
            if (qState.paused && !initial) return;
            // Не поллим, если вкладка браузера скрыта или активна вкладка схемы
            if (!initial && (document.hidden || activeTab !== 'queries')) return;

            try {
                const url = new URL(cfg.queriesUrl, window.location.origin);
                if (qState.lastId) url.searchParams.set('since', String(qState.lastId));
                const res = await fetch(url.toString(), { cache: 'no-store' });
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const data = await res.json();
                const items = data.queries || [];
                if (items.length) {
                    qState.lastId = items[items.length - 1].id;
                    prependQueries(items);
                    applySearchFilter();
                    scheduleChartUpdate();
                }
                updateKpi(data.stats || {});
            } catch (err) {
                console.error('pollQueries', err);
            }
        }
        function startPolling() {
            if (pollTimer) return;
            pollTimer = setInterval(() => pollQueries(false), POLL_MS);
        }

        // ---- events ----
        opChips.forEach((chip) => {
            chip.addEventListener('click', () => {
                opChips.forEach((c) => c.classList.toggle('active', c === chip));
                queriesList.dataset.opFilter = chip.dataset.opFilter;
            });
        });

        queriesSearch.addEventListener('input', debounce((e) => {
            qState.searchQuery = (e.target.value || '').trim().toLowerCase();
            applySearchFilter();
        }, 160));

        pauseBtn.addEventListener('click', () => {
            qState.paused = !qState.paused;
            pauseBtn.classList.toggle('is-paused', qState.paused);
            const icon = pauseBtn.querySelector('i');
            const label = pauseBtn.querySelector('span');
            if (qState.paused) {
                icon.className = 'bi bi-play-fill';
                label.textContent = 'Пауза';
            } else {
                icon.className = 'bi bi-pause-fill';
                label.textContent = 'Live';
                pollQueries(false);
            }
        });

        clearBtn.addEventListener('click', async () => {
            if (!confirm('Очистить буфер последних запросов? Это не затронет саму БД.')) return;
            try {
                const res = await fetch(cfg.clearUrl, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest' },
                });
                if (!res.ok) throw new Error('HTTP ' + res.status);
                queriesList.innerHTML = '';
                qState.cache.clear();
                qState.lastId = 0;
                doChartUpdate();
                updateKpi({ buffer_size: 0, avg_ms: 0, max_ms: 0, slow_count: 0 });
            } catch (err) {
                alert('Не удалось очистить буфер: ' + err.message);
            }
        });

        // ---- modal ----
        const modal = $('[data-role="modal"]');
        const modalBody = $('[data-role="modal-body"]');
        function openModal(q) {
            modalBody.innerHTML = `
                <dl class="db-modal-meta">
                    <div><dt>Операция</dt><dd>${escapeHtml(q.op)}</dd></div>
                    <div><dt>Время</dt><dd>${formatMs(q.duration_ms)}</dd></div>
                    <div><dt>Когда</dt><dd>${escapeHtml(fmtTs(q.ts))}</dd></div>
                    <div><dt>Пользователь</dt><dd>${escapeHtml(q.user || '—')}</dd></div>
                    <div><dt>Путь</dt><dd>${escapeHtml(q.path || '—')}</dd></div>
                    <div><dt>HTTP</dt><dd>${escapeHtml((q.method || '') + ' ' + (q.status || ''))}</dd></div>
                </dl>
                <pre>${highlightSql(q.sql || '')}</pre>
            `;
            modal.hidden = false;
            modal.setAttribute('aria-hidden', 'false');
        }
        $$('[data-role="modal-close"]').forEach((e) => {
            e.addEventListener('click', () => {
                modal.hidden = true;
                modal.setAttribute('aria-hidden', 'true');
            });
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !modal.hidden) {
                modal.hidden = true;
                modal.setAttribute('aria-hidden', 'true');
            }
        });

        // ---- start ----
        loadSchema();
        pollQueries(true);
        startPolling();

        // Pause timer when tab hidden (освобождаем CPU)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && activeTab === 'queries') pollQueries(false);
        });

        // Resize — fit ERD при ресайзе окна
        window.addEventListener('resize', debounce(() => {
            if (activeTab === 'schema' && erd.tables.length) {
                // Не фитим автоматически, чтобы не ломать расположение пользователя
                // Просто перерисуем рёбра (узлы в абсолютных координатах, так что не нужно)
            }
        }, 200));

        function debounce(fn, wait) {
            let t; return function (...args) {
                clearTimeout(t);
                t = setTimeout(() => fn.apply(this, args), wait);
            };
        }
    });
})();
