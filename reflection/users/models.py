# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"

    ROLE_CHOICES = [
        (USER, "Обычный пользователь"),
        (MODERATOR, "Модератор"),
        (ADMIN, "Администратор"),
    ]

    role = models.CharField(
        "Роль",
        max_length=20,
        choices=ROLE_CHOICES,
        default=USER,
    )

    def is_user(self):
        return self.role == self.USER

    def is_moderator(self):
        return self.role == self.MODERATOR

    def is_admin(self):
        return self.role == self.ADMIN
    
    def reviews_count(self):    
        """Возвращает количество записей пользователя, к которым привязан отзыв"""
        return self.bookings.filter(review__isnull=False).count()

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"