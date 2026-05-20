from django import forms
from django.core.exceptions import ValidationError
from .models import Service


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "short_description", "description", "duration", "price"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Название услуги"}
            ),
            "short_description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Краткое описание для карточки",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Полное описание методики",
                }
            ),
            "duration": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Например: 60 мин"}
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "0.00"}
            ),
        }

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise ValidationError("Введите название услуги.")
        if len(name) < 3:
            raise ValidationError("Название услуги должно содержать не менее 3 символов.")
        if len(name) > 255:
            raise ValidationError("Название услуги слишком длинное.")
        return name

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price < 0:
            raise ValidationError("Цена услуги не может быть отрицательной.")
        return price

