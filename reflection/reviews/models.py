from django.db import models
from django.utils import timezone


class Review(models.Model):
    name = models.CharField("Имя клиента", max_length=255)
    relation = models.CharField("Отношение к ребёнку", max_length=255, blank=True, null=True)
    content = models.TextField("Текст отзыва")
    booking = models.OneToOneField(
        "booking.Booking",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="review_link",  # это обратный путь: booking.review_link
    )
    created_at = models.DateTimeField("Дата отзыва", auto_now_add=True)

    def __str__(self):
        return f"{self.name} — {self.created_at.strftime('%d.%m.%Y')}"

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]