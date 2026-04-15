from django.db import models


class Service(models.Model):
    name = models.CharField("Название услуги", max_length=255)
    short_description = models.CharField("Краткое описание", max_length=512, blank=True, null=True)
    description = models.TextField("Описание", blank=True, null=True)
    duration = models.CharField("Длительность", max_length=100, blank=True, null=True)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
        ordering = ["name"]