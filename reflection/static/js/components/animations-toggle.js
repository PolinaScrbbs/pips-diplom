/* animations-toggle.js
 *
 * Пользовательский тумблер для отключения всех анимаций сайта
 * (включая анимации переходов между страницами).
 *
 * Первичное применение состояния происходит inline-скриптом в <head>
 * base.html — чтобы не было «вспышки» анимаций до гидрации. Здесь только
 * логика клика и синхронизация между вкладками.
 *
 * Состояние хранится в localStorage под ключом 'reflection.animations'.
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'reflection.animations';
    const DISABLED_CLASS = 'no-anim';

    function read() {
        try {
            return localStorage.getItem(STORAGE_KEY) === 'off' ? 'off' : 'on';
        } catch (_) { return 'on'; }
    }

    function write(value) {
        try { localStorage.setItem(STORAGE_KEY, value); } catch (_) { /* no-op */ }
    }

    function apply(state, btn) {
        const disabled = state === 'off';
        document.documentElement.classList.toggle(DISABLED_CLASS, disabled);
        if (btn) {
            btn.setAttribute('aria-pressed', disabled ? 'true' : 'false');
            btn.setAttribute(
                'title',
                disabled
                    ? 'Анимации переходов: выключены'
                    : 'Анимации переходов: включены'
            );
        }
    }

    function init() {
        const btn = document.querySelector('[data-role="anim-toggle"]');
        if (!btn) return;

        apply(read(), btn);

        btn.addEventListener('click', () => {
            const next = read() === 'off' ? 'on' : 'off';
            write(next);
            apply(next, btn);
        });

        /* Синхронизация между вкладками */
        window.addEventListener('storage', (e) => {
            if (e.key !== STORAGE_KEY) return;
            apply(read(), btn);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
