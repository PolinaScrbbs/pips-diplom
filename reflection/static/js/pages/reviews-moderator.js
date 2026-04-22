/* ==========================================================================
 * reviews-moderator.js — модалка с деталями отзыва.
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
    });
})();
