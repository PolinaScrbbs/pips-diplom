# booking/admin.py
from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    # Заменили category на service
    list_display = ["child_name", "parent_name", "user", "service", "phone", "created_at"]
    list_filter = ["service", "created_at", "user"]
    search_fields = ["child_name", "parent_name", "phone", "user__username"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("Аккаунт", {
            "fields": ("user",)
        }),
        ("Данные клиента", {
            "fields": ("child_name", "parent_name", "phone")
        }),
        ("Детали записи", {
            "fields": ("service", "comment")
        }),
        ("Дополнительно", {
            "fields": ("created_at", "review"),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'service', 'review')