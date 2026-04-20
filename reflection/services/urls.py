from django.urls import path
from . import views

app_name = "services"

urlpatterns = [
    path("", views.services, name="services"),
    path("load-more/", views.load_more_services, name="load_more_services"),
    path('<int:pk>/', views.service_detail, name='service_detail'),
    path("moderator-services-list/", views.moderator_services_list, name="moderator_list"),
    path("moderator-service-create/", views.service_create, name="service_create"),
]