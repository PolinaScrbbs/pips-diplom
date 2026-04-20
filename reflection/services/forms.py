from django import forms
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
