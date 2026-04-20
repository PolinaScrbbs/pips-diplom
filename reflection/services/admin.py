from django.contrib import admin
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "short_description", "duration", "price", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "short_description", "description"]
    ordering = ["name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("name", "short_description", "description")},
        ),
        ("Длительность и цена", {"fields": ("duration", "price")}),
        (
            "Системные поля",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
