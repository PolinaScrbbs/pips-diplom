from django.db import models
from reviews.models import Review


class Booking(models.Model):
    CHILD = "child"
    TEEN = "teen"
    FAMILY = "family"
    PARENTS = "parents"
    CATEGORY_CHOICES = [
        (CHILD, "Детская психология"),
        (TEEN, "Подростковые консультации"),
        (FAMILY, "Семейная психология"),
        (PARENTS, "Консультации для родителей"),
    ]

    child_name = models.CharField("Имя ребёнка", max_length=255)
    parent_name = models.CharField("Имя родителя", max_length=255)
    phone = models.CharField("Телефон", max_length=50)
    category = models.CharField("Категория", max_length=50, choices=CATEGORY_CHOICES)
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
        return f"{self.child_name} | {self.get_category_display()}"