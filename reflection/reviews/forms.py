from django import forms
from reviews.models import Review
import booking.models as booking_models
from services.models import Service


class SimpleReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["name", "relation", "content"]
        labels = {
            "name": "Ваше имя",
            "relation": "Отношение к ребёнку (по желанию)",
            "content": "Текст отзыва",
        }
        widgets = {
            "content": forms.Textarea(attrs={"rows": 4}),
        }


class ReviewCreateForm(forms.ModelForm):
    parent_name = forms.CharField(
        label="Ваше имя (родителя)",
        max_length=255,
        help_text="Впишите имя родителя, как в заказе.",
    )
    # Заменяем ChoiceField на ModelChoiceField
    service = forms.ModelChoiceField(
        label="Услуга",
        queryset=Service.objects.all(),
        empty_label="Выберите услугу",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    class Meta:
        model = Review
        # Заменили 'category' на 'service'
        fields = ["name", "relation", "parent_name", "service", "content"]
        labels = {
            "name": "Имя клиента (как в отзывах)",
            "relation": "Отношение к ребёнку",
            "content": "Текст отзыва",
        }
        widgets = {
            "content": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "relation": forms.TextInput(attrs={"class": "form-control"}),
            "parent_name": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        parent_name = cleaned.get("parent_name")
        service = cleaned.get("service")  # Теперь здесь объект Service

        if not parent_name or not service:
            # Ошибки для пустых полей Django добавит сам, но для логики clean это важно
            return cleaned

        # Ищем самый старый заказ по имени родителя и УСЛУГЕ (вместо категории)
        booking = (
            booking_models.Booking.objects.filter(
                parent_name=parent_name,
                service=service,  # Фильтруем по полю ForeignKey
                review__isnull=True,
            )
            .order_by("created_at")
            .first()
        )

        if not booking:
            raise forms.ValidationError(
                f"Для родителя '{parent_name}' и услуги '{service.name}' подходящего заказа нет "
                "или на все заказы уже оставлены отзывы."
            )

        # Сохраняем найденный booking в cleaned_data
        cleaned["booking"] = booking
        return cleaned
    parent_name = forms.CharField(
        label="Ваше имя (родителя)",
        max_length=255,
        help_text="Впишите имя родителя, как в заказе.",
    )
    # Теперь это выбор из модели Service
    service = forms.ModelChoiceField(
        label="Услуга",
        queryset=Service.objects.all(),
        empty_label="Выберите услугу",
        widget=forms.Select(attrs={"class": "form-control"})
    )