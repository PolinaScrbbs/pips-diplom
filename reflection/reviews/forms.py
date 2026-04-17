from django import forms
from reviews.models import Review
import booking.models as booking_models


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
    category = forms.ChoiceField(
        label="Категория услуги",
        choices=booking_models.Booking.CATEGORY_CHOICES,
    )

    class Meta:
        model = Review
        fields = ["name", "relation", "parent_name", "category", "content"]
        labels = {
            "name": "Имя клиента (как в отзывах)",
            "relation": "Отношение к ребёнку",
            "content": "Текст отзыва",
        }
        widgets = {
            "content": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        parent_name = cleaned.get("parent_name")
        category = cleaned.get("category")

        if not parent_name or not category:
            raise forms.ValidationError(
                "Поля 'Ваше имя' и 'Категория' обязательны."
            )

        # самый старый заказ без отзыва
        booking = (
            booking_models.Booking.objects.filter(
                parent_name=parent_name,
                category=category,
                review__isnull=True,
            )
            .order_by("created_at")
            .first()
        )

        if not booking:
            raise forms.ValidationError(
                "Для такого сочетания имени родителя и категории подходящего заказа нет "
                "или все заказы уже имеют отзывы."
            )

        cleaned["booking"] = booking
        return cleaned