from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    # Используем author__username для отображения имени пользователя
    list_display = ["author", "rating", "relation", "created_at"]
    list_filter = ["rating", "created_at"]
    # Поиск по юзернейму автора, отношению и тексту
    search_fields = ["author__username", "relation", "text"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at"]