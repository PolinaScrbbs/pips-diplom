/* ==========================================================================
 * service-detail.js — AOS + подставляем выбранную услугу в модалку записи.
 * ========================================================================== */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        if (typeof AOS !== 'undefined') {
            AOS.init({ duration: 800, once: true });
        }

        const bookingModal = document.getElementById('bookingModal');
        if (!bookingModal) return;

        bookingModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            if (!button) return;

            const serviceId = button.getAttribute('data-service-id');
            const serviceSelect = bookingModal.querySelector('select[name="service"]');

            if (serviceSelect && serviceId) {
                serviceSelect.value = serviceId;
            }
        });

        // ---------- Keyword tooltip (LLM) ----------
        const tip = document.createElement('div');
        tip.className = 'kw-tip';
        tip.hidden = true;
        tip.innerHTML = `
            <div class="kw-tip__head">
                <div class="kw-tip__word" id="kw-tip-word"></div>
                <div class="kw-tip__status" id="kw-tip-status"></div>
            </div>
            <div class="kw-tip__body" id="kw-tip-body"></div>
        `;
        document.body.appendChild(tip);

        const wordEl = tip.querySelector('#kw-tip-word');
        const statusEl = tip.querySelector('#kw-tip-status');
        const bodyEl = tip.querySelector('#kw-tip-body');

        let hoverTimer = null;
        let currentKw = null;
        let abortCtrl = null;

        function posTip(anchor) {
            const r = anchor.getBoundingClientRect();
            const pad = 10;
            const x = Math.min(window.innerWidth - 20, Math.max(10, r.left + window.scrollX));
            const y = r.bottom + window.scrollY + pad;
            tip.style.left = x + 'px';
            tip.style.top = y + 'px';
        }

        function showTip(anchor, kw) {
            currentKw = kw;
            if (wordEl) wordEl.textContent = kw;
            if (statusEl) statusEl.textContent = '…';
            if (bodyEl) bodyEl.textContent = 'Задаю вопрос нейросети…';
            posTip(anchor);
            tip.hidden = false;
        }

        function hideTip() {
            tip.hidden = true;
            currentKw = null;
            if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; }
            if (abortCtrl) { abortCtrl.abort(); abortCtrl = null; }
        }

        async function askKw(anchor, kw) {
            abortCtrl = new AbortController();
            const url = new URL('/services/keywords/ask/', window.location.origin);
            url.searchParams.set('word', kw);
            try {
                const res = await fetch(url.toString(), {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    signal: abortCtrl.signal,
                    cache: 'no-store',
                });
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const data = await res.json();
                if (!data || data.status !== 'success') throw new Error('Bad response');
                if (currentKw !== kw) return;
                if (statusEl) statusEl.textContent = 'готово';
                if (bodyEl) bodyEl.textContent = data.answer || '';
                posTip(anchor);
            } catch (e) {
                if (e.name === 'AbortError') return;
                if (statusEl) statusEl.textContent = 'ошибка';
                if (bodyEl) bodyEl.textContent = 'Не удалось получить ответ: ' + e.message;
            } finally {
                abortCtrl = null;
            }
        }

        document.addEventListener('mouseover', (e) => {
            const t = e.target;
            if (!(t instanceof HTMLElement)) return;
            if (!t.classList.contains('kw')) return;
            const kw = t.dataset.kw;
            if (!kw) return;
            if (hoverTimer) clearTimeout(hoverTimer);
            hoverTimer = setTimeout(() => {
                showTip(t, kw);
                askKw(t, kw);
            }, 220);
        });

        document.addEventListener('mouseout', (e) => {
            const t = e.target;
            if (!(t instanceof HTMLElement)) return;
            if (t.classList.contains('kw')) hideTip();
        });

        window.addEventListener('scroll', () => { if (!tip.hidden && document.activeElement) posTip(document.activeElement); }, { passive: true });
    });
})();
