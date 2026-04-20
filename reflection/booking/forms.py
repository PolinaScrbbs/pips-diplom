# booking/forms.py
from django import forms
from .models import Booking


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
