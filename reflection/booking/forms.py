# booking/forms.py
import re
from django import forms
from django.core.exceptions import ValidationError
from users.forms import PHONE_PATTERN
from .models import Booking

NAME_PATTERN = re.compile(r"^[A-Za-zА-Яа-яЁё\s-]+$")


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        # Убрали category, добавили service
        fields = ["child_name", "parent_name", "phone", "service", "comment"]
        widgets = {
            "child_name": forms.TextInput(attrs={"class": "form-control"}),
            "parent_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "type": "tel"}),
            "service": forms.Select(attrs={"class": "form-control"}),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = {
            "child_name": "Имя ребёнка",
            "parent_name": "Ваше имя (родитель)",
            "phone": "Телефон",
            "service": "Выберите услугу",
            "comment": "Комментарий (необязательно)",
        }

    def clean_child_name(self):
        name = (self.cleaned_data.get("child_name") or "").strip()
        if not name:
            raise ValidationError("Введите имя ребёнка.")
        if len(name) < 2:
            raise ValidationError("Имя должно содержать не менее 2 символов.")
        if len(name) > 100:
            raise ValidationError("Имя слишком длинное.")
        if not NAME_PATTERN.match(name):
            raise ValidationError("Имя может содержать только буквы, пробелы и дефисы.")
        return name

    def clean_parent_name(self):
        name = (self.cleaned_data.get("parent_name") or "").strip()
        if not name:
            raise ValidationError("Введите имя родителя.")
        if len(name) < 2:
            raise ValidationError("Имя должно содержать не менее 2 символов.")
        if len(name) > 100:
            raise ValidationError("Имя слишком длинное.")
        if not NAME_PATTERN.match(name):
            raise ValidationError("Имя может содержать только буквы, пробелы и дефисы.")
        return name

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            raise ValidationError("Введите номер телефона.")
        if not PHONE_PATTERN.match(phone):
            raise ValidationError("Формат телефона должен быть +7 (XXX) XXX-XX-XX.")
        return phone

