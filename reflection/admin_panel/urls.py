from django.urls import path

from admin_panel import views

app_name = "admin_panel"

urlpatterns = [
    path("", views.users_list, name="users_list"),
]
