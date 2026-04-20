# users/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={"minlength": 8}),
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise ValidationError("Этот логин уже занят.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким Email уже существует.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")

        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Пароли не совпадают.")

        if p1 and len(p1) < 8:
            self.add_error("password1", "Пароль должен быть не менее 8 символов.")

        return cleaned

    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

        labels = {
            "username": "Логин",
            "email": "Email",
        }

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Пароли не совпадают.")

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Логин",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Логин", "autofocus": True}
        ),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Пароль"}
        ),
    )

    error_messages = {
        "invalid_login": (
            "Неверный логин или пароль. Пожалуйста, проверьте раскладку клавиатуры и Caps Lock."
        ),
        "inactive": "Этот аккаунт деактивирован.",
    }

    def clean(self):
        # Стандартная проверка Django на существование пары логин/пароль
        return super().clean()
