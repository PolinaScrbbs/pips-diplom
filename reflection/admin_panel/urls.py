from django.urls import path

from admin_panel import views

app_name = "admin_panel"

urlpatterns = [
    path("", views.users_list, name="users_list"),
    path("users/create/", views.user_create, name="user_create"),
    path("users/<int:pk>/json/", views.user_detail_json, name="user_json"),
    path("users/<int:pk>/update/", views.user_update, name="user_update"),
    path("users/<int:pk>/toggle-active/", views.user_toggle_active, name="user_toggle"),
]
