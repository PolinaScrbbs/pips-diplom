from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Неизменяемая запись о действии над одной из отслеживаемых сущностей.
    Заполняется автоматически через signals + thread-local контекст из
    middleware. Никогда не редактируется и никогда не удаляется руками.
    """

    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_IMPERSONATE = "impersonate"
    ACTION_STOP_IMPERSONATE = "stop_impersonate"

    ACTION_CHOICES = [
        (ACTION_CREATE, "Создание"),
        (ACTION_UPDATE, "Изменение"),
        (ACTION_DELETE, "Удаление"),
        (ACTION_IMPERSONATE, "Вход за пользователя"),
        (ACTION_STOP_IMPERSONATE, "Возврат из impersonation"),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="Инициатор",
    )
    actor_username = models.CharField("Имя инициатора", max_length=150, blank=True)
    actor_role = models.CharField("Роль инициатора", max_length=20, blank=True)

    action = models.CharField("Действие", max_length=32, choices=ACTION_CHOICES)

    entity_type = models.CharField("Тип сущности", max_length=64, blank=True)
    entity_id = models.PositiveIntegerField("ID сущности", null=True, blank=True)
    entity_repr = models.CharField("Описание", max_length=255, blank=True)

    changes = models.JSONField("Изменения", default=dict, blank=True)

    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("User-Agent", max_length=255, blank=True)

    created_at = models.DateTimeField("Когда", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Событие аудита"
        verbose_name_plural = "Журнал аудита"
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["action"]),
            models.Index(fields=["actor"]),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} · {self.action} · {self.entity_type}#{self.entity_id}"
