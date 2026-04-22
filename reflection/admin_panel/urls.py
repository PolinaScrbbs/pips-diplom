from django.urls import path

from admin_panel import views

app_name = "admin_panel"

urlpatterns = [
    path("", views.users_list, name="users_list"),
    path("users/create/", views.user_create, name="user_create"),
    path("users/<int:pk>/json/", views.user_detail_json, name="user_json"),
    path("users/<int:pk>/update/", views.user_update, name="user_update"),
    path("users/<int:pk>/toggle-active/", views.user_toggle_active, name="user_toggle"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),

    path("logs/", views.logs_page, name="logs"),
    path("logs/stream/", views.logs_stream, name="logs_stream"),
    path("logs/dates/", views.logs_dates, name="logs_dates"),
    path("logs/users/", views.logs_users, name="logs_users"),
    path("logs/clear/", views.logs_clear, name="logs_clear"),
    path("logs/download/", views.logs_download, name="logs_download"),

    path("stats/", views.stats_page, name="stats"),
    path("stats/data/", views.stats_data, name="stats_data"),

    path("audit/", views.audit_page, name="audit"),
    path("audit/data/", views.audit_data, name="audit_data"),
    path("audit/filters/", views.audit_filters, name="audit_filters"),
    path("audit/<int:pk>/", views.audit_detail, name="audit_detail"),

    path("users/<int:pk>/impersonate/", views.impersonate_user, name="impersonate"),
    path("stop-impersonation/", views.stop_impersonation, name="stop_impersonation"),

    path("db/", views.db_page, name="db"),
    path("db/schema/", views.db_schema, name="db_schema"),
    path("db/queries/", views.db_queries, name="db_queries"),
    path("db/queries/clear/", views.db_queries_clear, name="db_queries_clear"),
]
