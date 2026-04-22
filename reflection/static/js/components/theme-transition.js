/* theme-transition.js
 *
 * Перехватывает клик по ссылке, ведущей в другую цветовую тему (обычная ↔
 * терминальная страница системных логов), запускает «волну» из точки клика,
 * а затем выполняет реальный переход.
 *
 * Incoming-сторона анимации (раскрытие из точки на новой странице) делается
 * inline-бутстрапом в base.html: он создаёт overlay до первой отрисовки.
 *
 * Координаты точки-источника передаются между страницами через sessionStorage
 * как доли от размеров вьюпорта — чтобы анимация ощущалась как одно
 * непрерывное движение даже при разной верстке источника и приёмника.
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'reflection.themeTransition';
    const OUTGOING_DURATION = 700;
    const SAFETY_TIMEOUT = 1500;
    const MOTION_QUERY = window.matchMedia('(prefers-reduced-motion: reduce)');

    /* Регистрируем «зоны» — визуально различающиеся разделы сайта.
     * Анимация смены темы запускается, когда переходим из одной зоны в другую. */
    const ZONE_PREFIXES = [
        { zone: 'dark',  prefix: '/admin-panel/logs' },
        { zone: 'stats', prefix: '/admin-panel/stats' },
        { zone: 'db',    prefix: '/admin-panel/db' },
        { zone: 'audit', prefix: '/admin-panel/audit' },
    ];
    const BODY_ZONE_CLASSES = [
        { cls: 'page-admin-logs',  zone: 'dark' },
        { cls: 'page-admin-stats', zone: 'stats' },
        { cls: 'page-admin-db',    zone: 'db' },
        { cls: 'page-admin-audit', zone: 'audit' },
    ];

    function zoneFromPath(href) {
        try {
            const url = new URL(href, window.location.origin);
            if (url.origin !== window.location.origin) return null;
            for (const item of ZONE_PREFIXES) {
                if (url.pathname.startsWith(item.prefix)) return item.zone;
            }
            return 'light';
        } catch (_) {
            return null;
        }
    }

    function currentZone() {
        for (const item of BODY_ZONE_CLASSES) {
            if (document.body.classList.contains(item.cls)) return item.zone;
        }
        return 'light';
    }

    function labelMarkup() {
        return (
            '<span class="tt-label-dark">&gt; booting reflection.shell</span>' +
            '<span class="tt-label-light">' +
                '<span class="tt-label-icon">❀</span>' +
                '<span class="tt-label-title">Отражение</span>' +
                '<span class="tt-label-subtitle">детский центр</span>' +
            '</span>' +
            '<span class="tt-label-stats">' +
                '<span class="tt-label-bars" aria-hidden="true">' +
                    '<span></span><span></span><span></span><span></span>' +
                '</span>' +
                '<span class="tt-label-title">Аналитика</span>' +
                '<span class="tt-label-subtitle">центр управления</span>' +
            '</span>' +
            '<span class="tt-label-db">' +
                '<span class="tt-title-huge" aria-label="БД">' +
                    '<span>Б</span><span>Д</span>' +
                '</span>' +
                '<span class="tt-accent-line" aria-hidden="true"></span>' +
                '<span class="tt-label-subtitle">database · schema</span>' +
            '</span>' +
            '<span class="tt-label-audit">' +
                '<span class="tt-title-huge" aria-label="Аудит">' +
                    '<span>А</span><span>у</span><span>д</span><span>и</span><span>т</span>' +
                '</span>' +
                '<span class="tt-accent-line" aria-hidden="true"></span>' +
                '<span class="tt-label-subtitle">audit · trail</span>' +
            '</span>'
        );
    }

    function buildOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'theme-transition-overlay';
        overlay.setAttribute('aria-hidden', 'true');

        ['tt-bg', 'tt-ring', 'tt-label'].forEach((cls) => {
            const n = document.createElement('div');
            n.className = cls;
            if (cls === 'tt-label') n.innerHTML = labelMarkup();
            overlay.appendChild(n);
        });
        return overlay;
    }

    function ensureOverlay() {
        let el = document.getElementById('theme-transition-overlay');
        if (!el) {
            el = buildOverlay();
            document.body.appendChild(el);
        } else {
            // Если overlay уже есть (например, от incoming-бутстрапа) — сбрасываем.
            el.className = '';
        }
        return el;
    }

    function setOrigin(overlay, xRatio, yRatio) {
        const x = Math.max(0, Math.min(1, xRatio)) * window.innerWidth;
        const y = Math.max(0, Math.min(1, yRatio)) * window.innerHeight;
        overlay.style.setProperty('--tt-x', `${x}px`);
        overlay.style.setProperty('--tt-y', `${y}px`);
    }

    function playOutgoing(direction, xRatio, yRatio) {
        const overlay = ensureOverlay();
        void overlay.offsetWidth;
        setOrigin(overlay, xRatio, yRatio);
        overlay.classList.add('tt-out', `tt-${direction}`, 'is-active');

        return new Promise((resolve) => {
            const bg = overlay.querySelector('.tt-bg');
            const onEnd = (ev) => {
                if (ev.target === bg) {
                    cleanup();
                    resolve();
                }
            };
            const cleanup = () => {
                overlay.removeEventListener('animationend', onEnd);
                clearTimeout(timer);
            };
            overlay.addEventListener('animationend', onEnd);
            const timer = setTimeout(() => {
                cleanup();
                resolve();
            }, OUTGOING_DURATION + SAFETY_TIMEOUT);
        });
    }

    function isModifiedClick(e) {
        return (
            e.button !== 0 ||
            e.metaKey || e.ctrlKey || e.shiftKey || e.altKey
        );
    }

    function animationsDisabled() {
        return document.documentElement.classList.contains('no-anim');
    }

    function handleLinkClick(e) {
        if (e.defaultPrevented || isModifiedClick(e)) return;
        if (animationsDisabled()) return;
        const link = e.target.closest('a');
        if (!link) return;
        if (link.target && link.target !== '_self' && link.target !== '') return;
        if (link.hasAttribute('download')) return;

        const href = link.getAttribute('href');
        if (!href) return;
        if (
            href.startsWith('#') || href.startsWith('mailto:') ||
            href.startsWith('tel:') || href.startsWith('javascript:')
        ) return;

        const toZone = zoneFromPath(link.href);
        if (toZone === null) return;
        const fromZone = currentZone();
        if (fromZone === toZone) return;
        const direction = 'to-' + toZone;

        try {
            const a = new URL(link.href, window.location.origin);
            if (a.pathname === window.location.pathname && a.search === window.location.search) return;
        } catch (_) { /* ignore */ }

        e.preventDefault();

        const cx = e.clientX || link.getBoundingClientRect().left + link.offsetWidth / 2;
        const cy = e.clientY || link.getBoundingClientRect().top + link.offsetHeight / 2;
        const xRatio = cx / window.innerWidth;
        const yRatio = cy / window.innerHeight;

        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
                direction,
                x: xRatio,
                y: yRatio,
            }));
        } catch (_) { /* no-op */ }

        const dur = MOTION_QUERY.matches ? 250 : OUTGOING_DURATION;
        let navigated = false;
        const navigate = () => {
            if (navigated) return;
            navigated = true;
            window.location.href = link.href;
        };

        playOutgoing(direction, xRatio, yRatio).then(navigate);
        setTimeout(navigate, dur + SAFETY_TIMEOUT);
    }

    document.addEventListener('click', handleLinkClick, true);

    // Если страница восстановлена из bfcache — оверлей мог остаться. Прибираем.
    window.addEventListener('pageshow', (ev) => {
        if (!ev.persisted) return;
        const overlay = document.getElementById('theme-transition-overlay');
        if (overlay) overlay.className = '';
    });
})();
