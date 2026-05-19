# users/forms.py
import re

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.core.exceptions import ValidationError

User = get_user_model()

USERNAME_PATTERN = re.compile(r"^[\w.@+-]+$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Пароль",
                "minlength": "8",
                "autocomplete": "new-password",
            }
        ),
        error_messages={"required": "Введите пароль."},
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Повтор пароля",
                "autocomplete": "new-password",
            }
        ),
        error_messages={"required": "Подтвердите пароль."},
    )

    class Meta:
        model = User
        fields = ["username", "email"]
        labels = {
            "username": "Логин",
            "email": "Email",
        }
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Логин",
                    "minlength": "3",
                    "maxlength": "150",
                    "pattern": r"[\w.@+-]+",
                    "autocomplete": "username",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "name@example.com",
                    "autocomplete": "email",
                }
            ),
        }
        error_messages = {
            "username": {"required": "Введите логин."},
            "email": {"required": "Введите email."},
        }

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise ValidationError("Введите логин.")

        if len(username) < 3:
            raise ValidationError("Логин должен содержать не менее 3 символов.")

        if len(username) > 150:
            raise ValidationError("Логин не может быть длиннее 150 символов.")

        if not USERNAME_PATTERN.match(username):
            raise ValidationError(
                "Логин может содержать только буквы, цифры и символы @ . + - _."
            )

        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Этот логин уже занят.")

        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise ValidationError("Введите email.")

        if not EMAIL_PATTERN.match(email):
            raise ValidationError("Введите корректный адрес email.")

        if len(email) > 254:
            raise ValidationError("Email слишком длинный.")

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Пользователь с таким email уже существует.")

        return email

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if not password:
            raise ValidationError("Введите пароль.")

        if len(password) < 8:
            raise ValidationError("Пароль должен быть не менее 8 символов.")

        user = User(
            username=self.cleaned_data.get("username", ""),
            email=self.cleaned_data.get("email", ""),
        )
        try:
            password_validation.validate_password(password, user)
        except ValidationError as exc:
            raise ValidationError(exc.messages) from exc

        return password

    def clean_password2(self):
        password2 = self.cleaned_data.get("password2")
        if not password2:
            raise ValidationError("Подтвердите пароль.")
        return password2

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Пароли не совпадают.")

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = UsernameField(
        label="Логин",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Логин",
                "autofocus": True,
                "autocomplete": "username",
                "minlength": "1",
                "maxlength": "150",
            }
        ),
        error_messages={"required": "Введите логин."},
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Пароль",
                "autocomplete": "current-password",
            }
        ),
        error_messages={"required": "Введите пароль."},
    )

    error_messages = {
        "invalid_login": (
            "Неверный логин или пароль. "
            "Проверьте раскладку клавиатуры и Caps Lock."
        ),
        "inactive": "Этот аккаунт деактивирован. Обратитесь к администратору.",
    }

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise ValidationError("Введите логин.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not password:
            raise ValidationError("Введите пароль.")
        return password
