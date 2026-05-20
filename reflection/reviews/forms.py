from django import forms
from django.core.exceptions import ValidationError
from .models import Review


class ReviewCreateForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "relation", "text"]  # Поля, которые заполняет юзер

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if rating is None or rating < 1 or rating > 5:
            raise ValidationError("Оценка должна быть от 1 до 5.")
        return rating

    def clean_relation(self):
        relation = (self.cleaned_data.get("relation") or "").strip()
        if not relation:
            raise ValidationError("Пожалуйста, укажите кем вы приходитесь ребенку.")
        if len(relation) < 2:
            raise ValidationError("Это поле должно содержать не менее 2 символов.")
        if len(relation) > 255:
            raise ValidationError("Текст слишком длинный.")
        return relation

    def clean_text(self):
        text = (self.cleaned_data.get("text") or "").strip()
        if not text:
            raise ValidationError("Текст отзыва не может быть пустым.")
        if len(text) < 10:
            raise ValidationError("Текст отзыва должен быть не менее 10 символов.")
        return text

