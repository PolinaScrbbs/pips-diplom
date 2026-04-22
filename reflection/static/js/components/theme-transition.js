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
    const DARK_PATH_PREFIX = '/admin-panel/logs';
    const OUTGOING_DURATION = 700;
    const SAFETY_TIMEOUT = 1500;
    const MOTION_QUERY = window.matchMedia('(prefers-reduced-motion: reduce)');

    function isDarkPath(href) {
        try {
            const url = new URL(href, window.location.origin);
            if (url.origin !== window.location.origin) return null;
            return url.pathname.startsWith(DARK_PATH_PREFIX);
        } catch (_) {
            return null;
        }
    }

    function currentlyDark() {
        return document.body.classList.contains('page-admin-logs');
    }

    function buildOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'theme-transition-overlay';
        overlay.setAttribute('aria-hidden', 'true');

        ['tt-bg', 'tt-ring', 'tt-label'].forEach((cls) => {
            const n = document.createElement('div');
            n.className = cls;
            if (cls === 'tt-label') {
                n.innerHTML =
                    '<span class="tt-label-dark">&gt; booting reflection.shell</span>' +
                    '<span class="tt-label-light">' +
                        '<span class="tt-label-icon">❀</span>' +
                        '<span class="tt-label-title">Отражение</span>' +
                        '<span class="tt-label-subtitle">детский центр</span>' +
                    '</span>';
            }
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

    function handleLinkClick(e) {
        if (e.defaultPrevented || isModifiedClick(e)) return;
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

        const targetIsDark = isDarkPath(link.href);
        if (targetIsDark === null) return;

        const fromDark = currentlyDark();
        let direction;
        if (!fromDark && targetIsDark) direction = 'to-dark';
        else if (fromDark && !targetIsDark) direction = 'to-light';
        else return;

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
