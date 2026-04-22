from django.apps import AppConfig


class AdminPanelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "admin_panel"
    verbose_name = "Панель администратора"

    def ready(self):
        from admin_panel import signals
        signals.register()
