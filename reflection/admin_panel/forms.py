from django import forms

from users.models import User


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(label="Пароль", widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(
        label="Повторите пароль", widget=forms.PasswordInput, required=True
    )
    role = forms.ChoiceField(
        label="Роль",
        choices=[
            (User.USER, "Обычный пользователь"),
            (User.MODERATOR, "Модератор"),
        ],
        required=True,
    )

    class Meta:
        model = User
        fields = ("username", "email", "phone", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Разрешаем создавать пользователя без email/phone
        self.fields["email"].required = False
        self.fields["phone"].required = False

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Пароли не совпадают.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_active = True
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Новый пароль (необязательно)", widget=forms.PasswordInput, required=False
    )
    password2 = forms.CharField(
        label="Подтвердите новый пароль", widget=forms.PasswordInput, required=False
    )

    class Meta:
        model = User
        fields = ("username", "email", "phone", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = False
        self.fields["phone"].required = False

        # Нельзя назначать роль admin, но существующий admin может оставаться admin
        if self.instance and self.instance.pk and self.instance.role == User.ADMIN:
            self.fields["role"].choices = [
                (User.ADMIN, "Администратор"),
                (User.USER, "Обычный пользователь"),
                (User.MODERATOR, "Модератор"),
            ]
        else:
            self.fields["role"].choices = [
                (User.USER, "Обычный пользователь"),
                (User.MODERATOR, "Модератор"),
            ]

    def clean_role(self):
        role = self.cleaned_data.get("role")
        if role == User.ADMIN and (not self.instance or self.instance.role != User.ADMIN):
            raise forms.ValidationError("Нельзя назначать роль администратора.")
        return role

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1") or ""
        p2 = cleaned.get("password2") or ""

        if p1 or p2:
            if not p1:
                self.add_error("password1", "Введите новый пароль.")
            if not p2:
                self.add_error("password2", "Подтвердите новый пароль.")
            if p1 and p2 and p1 != p2:
                self.add_error("password2", "Пароли не совпадают.")

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get("password1")
        if new_password:
            user.set_password(new_password)
        if commit:
            user.save()
        return user

