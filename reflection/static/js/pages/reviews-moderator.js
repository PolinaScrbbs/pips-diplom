/* ==========================================================================
 * reviews-moderator.js — модалка + фильтры/поиск без перезагрузки.
 * ========================================================================== */
(function () {
    'use strict';

    let reviewModal = null;

    function ensureModal() {
        if (reviewModal) return reviewModal;
        const el = document.getElementById('reviewDetailModal');
        if (el && typeof bootstrap !== 'undefined') {
            reviewModal = new bootstrap.Modal(el);
        }
        return reviewModal;
    }

    window.viewReview = function (author, rating, text, date) {
        const modal = ensureModal();
        if (!modal) {
            console.error('Bootstrap модалка недоступна');
            return;
        }

        document.getElementById('modal-author').innerText = author;
        document.getElementById('modal-date').innerText = date;
        document.getElementById('modal-text').innerText = text;

        const avatar = document.getElementById('modal-avatar');
        if (avatar) {
            avatar.innerText = (author || '?').trim().charAt(0).toUpperCase();
        }

        let starsHtml = '';
        const r = parseInt(rating, 10);
        for (let i = 1; i <= 5; i++) {
            starsHtml += `<i class="bi ${i <= r ? 'bi-star-fill' : 'bi-star'}"></i>`;
        }
        document.getElementById('modal-rating').innerHTML = starsHtml;

        modal.show();
    };

    document.addEventListener('DOMContentLoaded', function () {
        ensureModal();

        const toolbar = document.getElementById('mod-toolbar-reviews');
        const results = document.getElementById('mod-results-reviews');
        if (!toolbar || !results) return;

        function setActiveChip(rating) {
            const val = (rating || '').trim();
            toolbar.querySelectorAll('button[data-rating]').forEach((btn) => {
                btn.classList.toggle('is-active', (btn.dataset.rating || '') === val);
            });
        }

        function applyStateToUI(sp) {
            const searchEl = toolbar.querySelector('input[name="search"]');
            const rating = (sp.get('rating') || '').trim();
            if (searchEl) searchEl.value = (sp.get('search') || '').trim();
            setActiveChip(rating);
        }

        function qsFromToolbar(extra) {
            const fd = new FormData(toolbar);
            const sp = new URLSearchParams();
            for (const [k, v] of fd.entries()) {
                const val = String(v || '').trim();
                if (!val) continue;
                sp.set(k, val);
            }
            if (extra) {
                Object.keys(extra).forEach((k) => {
                    const v = extra[k];
                    const val = String(v || '').trim();
                    if (!val) sp.delete(k);
                    else sp.set(k, val);
                });
            }
            if (!extra || !Object.prototype.hasOwnProperty.call(extra, 'page')) sp.delete('page');
            return sp;
        }

        async function fetchAndRender(sp) {
            const url = `${window.location.pathname}?${sp.toString()}`;
            const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
            const data = await res.json();
            if (!data || data.status !== 'success') return;
            results.innerHTML = data.html || '';
            window.history.replaceState({}, '', url);
            applyStateToUI(sp);
            wireRows();
        }

        function wireRows() {
            document.querySelectorAll('.review-row').forEach((row) => {
                if (row.__wired) return;
                row.__wired = true;
                const open = function () {
                    const author = row.dataset.reviewAuthor || '';
                    const rating = row.dataset.reviewRating || '';
                    const text = row.dataset.reviewText || '';
                    const date = row.dataset.reviewDate || '';
                    window.viewReview(author, rating, text, date);
                };
                row.addEventListener('click', function (e) {
                    if (e.target.closest('button')) return;
                    open();
                });
                row.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter' || e.key === ' ') open();
                });
            });
        }

        // chips: делаем кнопками без submit
        toolbar.querySelectorAll('.mod-toolbar__chips button[name="rating"]').forEach((btn) => {
            btn.type = 'button';
            btn.dataset.rating = btn.value || '';
            btn.removeAttribute('name');
            btn.addEventListener('click', function () {
                setActiveChip(this.dataset.rating || '');
                fetchAndRender(qsFromToolbar({ rating: this.dataset.rating || '' }));
            });
        });

        // search debounce
        const searchEl = toolbar.querySelector('input[name="search"]');
        let t = null;
        if (searchEl) {
            searchEl.addEventListener('input', function () {
                if (t) window.clearTimeout(t);
                t = window.setTimeout(() => fetchAndRender(qsFromToolbar()), 300);
            });
        }

        toolbar.addEventListener('submit', function (e) {
            e.preventDefault();
            fetchAndRender(qsFromToolbar());
        });

        // pagination
        results.addEventListener('click', function (e) {
            const a = e.target.closest('a');
            if (!a) return;
            const href = a.getAttribute('href') || '';
            if (!href.startsWith('?')) return;
            e.preventDefault();
            fetchAndRender(new URLSearchParams(href.replace(/^\?/, '')));
        });

        applyStateToUI(new URLSearchParams(window.location.search.replace(/^\?/, '')));
        wireRows();
    });
})();
