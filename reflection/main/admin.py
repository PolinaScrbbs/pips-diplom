from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["child_name", "parent_name", "phone", "category", "created_at"]
    list_filter = ["category", "created_at"]
    search_fields = ["child_name", "parent_name", "phone"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("Данные ребёнка и родителя", {
            "fields": ("child_name", "parent_name", "phone")
        }),
        ("Категория и комментарий", {
            "fields": ("category", "comment")
        }),
        ("Системная информация", {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )