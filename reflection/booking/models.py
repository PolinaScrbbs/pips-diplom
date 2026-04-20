# booking/models.py
from django.db import models
from django.conf import settings
from reviews.models import Review
from services.models import Service


class Booking(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        verbose_name="Пользователь",
        null=True,
        blank=True,
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        verbose_name="Услуга",
        related_name="bookings",
    )
    child_name = models.CharField("Имя ребёнка", max_length=255)
    parent_name = models.CharField("Имя родителя", max_length=255)
    phone = models.CharField("Телефон", max_length=50)
    comment = models.TextField("Комментарий", blank=True, null=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    review = models.OneToOneField(
        Review,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="linked_booking",
    )

    def __str__(self):
        # Теперь берем название из связанной модели Service
        return f"{self.child_name} | {self.service.name}"
