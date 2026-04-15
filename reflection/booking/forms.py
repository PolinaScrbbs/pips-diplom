from django import forms
from .models import Booking

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["child_name", "parent_name", "phone", "category", "comment"]
        widgets = {
            "child_name": forms.TextInput(attrs={"class": "form-control"}),
            "parent_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "type": "tel"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = {
            "child_name": "Имя ребёнка",
            "parent_name": "Ваше имя (родитель)",
            "phone": "Телефон",
            "category": "Категория обращения",
            "comment": "Комментарий (необязательно)",
        }