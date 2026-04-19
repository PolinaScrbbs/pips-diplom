from django import forms
from .models import Review

class ReviewCreateForm(forms.ModelForm):
    """Форма для создания отзыва, привязанного к Booking"""
    class Meta:
        model = Review
        fields = ["name", "relation", "content"]
        labels = {
            "name": "Ваше имя",
            "relation": "Отношение к ребёнку (напр. Мама)",
            "content": "Текст отзыва",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Введите ваше имя"}),
            "relation": forms.TextInput(attrs={"class": "form-control", "placeholder": "Мама / Папа / Родственник"}),
            "content": forms.Textarea(attrs={"rows": 4, "class": "form-control", "placeholder": "Ваши впечатления..."}),
        }