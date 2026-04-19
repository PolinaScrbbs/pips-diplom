from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Добавляем поле role в список отображения
    list_display = ("username", "email", "first_name", "last_name", "role", "reviews_count_display", "is_staff")
    
    # Добавляем фильтрацию по ролям в боковую панель
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    
    # Настраиваем группы полей в форме редактирования пользователя
    # Добавляем роль в секцию "Personal info" или создаем свою
    fieldsets = UserAdmin.fieldsets + (
        ("Дополнительные права", {"fields": ("role",)}),
    )
    
    # Аналогично для формы создания пользователя
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Дополнительные права", {"fields": ("role",)}),
    )

    # Кастомная колонка для отображения количества отзывов
    @admin.display(description="Отзывов")
    def reviews_count_display(self, obj):
        return obj.reviews_count()