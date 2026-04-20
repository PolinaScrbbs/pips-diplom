from django.urls import path
from reviews import views

app_name = "reviews"

urlpatterns = [
    path("", views.reviews, name="reviews"),
    path("create/", views.create_review, name="create_review"),
    path('moderator-reviews-list/', views.moderator_reviews_list, name='moderator_reviews'),
]