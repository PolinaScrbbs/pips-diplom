from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["name", "relation", "created_at"]
    search_fields = ["name", "relation", "content"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at"]