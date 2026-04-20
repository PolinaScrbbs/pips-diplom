from django.db import models
from django.conf import settings  # Для связи с моделью пользователя
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    # Связываем с пользователем. При удалении пользователя удалятся и его отзывы.
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Автор",
    )

    relation = models.CharField(
        "Отношение к ребёнку", max_length=255, blank=True, null=True
    )
    text = models.TextField("Текст отзыва")

    rating = models.PositiveSmallIntegerField(
        "Оценка", default=5, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    booking = models.OneToOneField(
        "booking.Booking",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="review_link",
    )

    created_at = models.DateTimeField("Дата отзыва", auto_now_add=True)

    def __str__(self):
        return f"Отзыв от {self.author.username} ({self.rating}★)"

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]
