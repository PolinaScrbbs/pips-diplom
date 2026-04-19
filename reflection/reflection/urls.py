from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("", include("main.urls")),
    path("services/", include("services.urls")),
    path("reviews/", include("reviews.urls")),
    path("booking/", include("booking.urls")),
    path("users/", include("users.urls")),
    path("admin/", admin.site.urls),
]