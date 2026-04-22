from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    path("", views.index, name="index"),
    path("why-us/", views.why_us, name="why_us"),
    path(
        "moderator/preview/start/",
        views.start_moderator_preview,
        name="start_moderator_preview",
    ),
    path(
        "moderator/preview/stop/",
        views.stop_moderator_preview,
        name="stop_moderator_preview",
    ),
]
