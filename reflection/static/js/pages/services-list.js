/* ==========================================================================
 * services-list.js — инициализация AOS и подгрузка следующих страниц услуг.
 * ========================================================================== */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        if (typeof AOS !== 'undefined') {
            AOS.init({ duration: 800, once: true });
        }

        const container = document.getElementById('services-container');
        const btn = document.getElementById('load-more-btn');
        if (!btn || !container) return;

        btn.addEventListener('click', function () {
            const nextPage = this.getAttribute('data-next-page');
            const url = this.getAttribute('data-url');

            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Загружаем...';

            const csrfEl = document.querySelector('[name=csrfmiddlewaretoken]');
            const csrfToken = csrfEl ? csrfEl.value : '';

            fetch(`${url}?page=${nextPage}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken,
                },
            })
                .then((r) => r.json())
                .then((data) => {
                    data.items.forEach((item) => {
                        const div = document.createElement('div');
                        div.className = 'col-lg-4 col-md-6 service-item';
                        div.setAttribute('data-aos', 'fade-up');

                        const shortDesc = item.short_description
                            ? `<p class="text-muted small mb-3"><strong>${item.short_description}</strong></p>`
                            : '';

                        div.innerHTML = `
                            <div class="card h-100 border-0 shadow-sm service-card">
                                <div class="card-body d-flex flex-column">
                                    <div class="d-flex justify-content-between align-items-start mb-3">
                                        <h4 class="service-title mb-0">${item.name}</h4>
                                        <i class="bi bi-patch-check text-success fs-5"></i>
                                    </div>
                                    ${shortDesc}
                                    <p class="text-secondary small flex-grow-1">${item.description}</p>
                                    <div class="mt-4 pt-3 border-top d-flex justify-content-between align-items-center">
                                        <div class="text-muted small"><i class="bi bi-clock me-1"></i> ${item.duration || '—'}</div>
                                        <div class="price-tag">${item.price || '0'} ₽</div>
                                    </div>
                                </div>
                            </div>
                        `;
                        container.appendChild(div);
                    });

                    if (typeof AOS !== 'undefined') AOS.refresh();

                    if (data.has_next) {
                        btn.setAttribute('data-next-page', parseInt(nextPage, 10) + 1);
                        btn.disabled = false;
                        btn.innerHTML = originalText;
                    } else {
                        btn.remove();
                    }
                })
                .catch(() => {
                    alert('Ошибка загрузки. Попробуйте обновить страницу.');
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                });
        });
    });
})();
