from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    path("", views.home, name="home"),
    path("services/", views.services, name="services"),
    path("why-us/", views.why_us, name="why_us"),
    path("reviews/", views.reviews, name="reviews"),
]
