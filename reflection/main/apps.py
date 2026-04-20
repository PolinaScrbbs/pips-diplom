# services/apps.py
from django.apps import AppConfig
import sys
import os


class ServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "main"

    def ready(self):
        # Чтобы избежать "populate() isn't reentrant", запускаем логику только
        # когда основной поток runserver готов
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") == "true":
            # Импортируем внутри, чтобы не ломать загрузку
            from . import setup_logic

            setup_logic.run()
