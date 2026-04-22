from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", include("main.urls")),
    path("services/", include("services.urls")),
    path("reviews/", include("reviews.urls")),
    path("booking/", include("booking.urls")),
    path("users/", include("users.urls")),
    path("admin-panel/", include("admin_panel.urls")),
    path("admin/", admin.site.urls),
]

# Кастомные обработчики ошибок.
# Django подключает их автоматически как handler404/handler403 при DEBUG=False.
handler404 = "main.views.custom_page_not_found"
handler403 = "main.views.custom_permission_denied"

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
