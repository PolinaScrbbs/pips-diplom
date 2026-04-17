from django.urls import path
from reviews import views

app_name = "reviews"

urlpatterns = [
    path("", views.reviews, name="reviews"),
    path("create-simple/", views.create_simple_review, name="create_simple_review"),
    path("create/", views.create_review, name="create_review"),
]