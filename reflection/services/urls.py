from django.urls import path
from . import views

app_name = "services"

urlpatterns = [
    path("", views.services, name="services"),
    path("load-more/", views.load_more_services, name="load_more_services"),
    path("keywords/ask/", views.keyword_ask, name="keyword_ask"),
    path("<int:pk>/", views.service_detail, name="service_detail"),
    path(
        "moderator-services-list/", views.moderator_services_list, name="moderator_list"
    ),
    path("moderator-service-create/", views.service_create, name="service_create"),
    path(
        "moderator/service/<int:pk>/json/",
        views.service_detail_json,
        name="service_json",
    ),
    path(
        "moderator/service/<int:pk>/update/",
        views.service_update,
        name="service_update",
    ),
    path(
        "moderator/service/<int:pk>/toggle/",
        views.service_toggle_visibility,
        name="service_toggle",
    ),
    path(
        "moderator/service/<int:pk>/delete/",
        views.service_delete,
        name="service_delete",
    ),
]
