from django.db import models
from django.utils import timezone

class Booking(models.Model):
    CATEGORY_CHOICES = [
        ("", "Выберите"),
        ("child", "Детская психология"),
        ("teen", "Подростковые консультации"),
        ("family", "Семейная психология"),
        ("parents", "Консультации для родителей"),
    ]

    child_name = models.CharField("Имя ребёнка", max_length=255)
    parent_name = "Ваше имя (родитель)"
    parent_name = models.CharField("Ваше имя (родитель)", max_length=255)
    phone = models.CharField("Телефон", max_length=50)
    category = models.CharField("Категория", max_length=50, choices=CATEGORY_CHOICES)
    comment = models.TextField("Комментарий", blank=True, null=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    def __str__(self):
        return f"{self.child_name} | {self.category} | {self.created_at.strftime('%d.%m.%Y')}"

