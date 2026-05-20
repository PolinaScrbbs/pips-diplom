from django import forms
from django.contrib.auth import password_validation
from users.models import User
from users.forms import USERNAME_PATTERN, EMAIL_PATTERN, PHONE_PATTERN


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

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise forms.ValidationError("Введите логин.")

        if len(username) < 3:
            raise forms.ValidationError("Логин должен содержать не менее 3 символов.")

        if len(username) > 150:
            raise forms.ValidationError("Логин не может быть длиннее 150 символов.")

        if not USERNAME_PATTERN.match(username):
            raise forms.ValidationError(
                "Логин может содержать только буквы, цифры и символы @ . + - _."
            )

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Этот логин уже занят.")

        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return email

        if not EMAIL_PATTERN.match(email):
            raise forms.ValidationError("Введите корректный адрес email.")

        if len(email) > 254:
            raise forms.ValidationError("Email слишком длинный.")

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует.")

        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return phone

        if not PHONE_PATTERN.match(phone):
            raise forms.ValidationError("Формат телефона должен быть +7 (XXX) XXX-XX-XX.")
        return phone

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if not password:
            raise forms.ValidationError("Введите пароль.")

        if len(password) < 8:
            raise forms.ValidationError("Пароль должен быть не менее 8 символов.")

        user = User(
            username=self.cleaned_data.get("username", ""),
            email=self.cleaned_data.get("email", ""),
        )
        try:
            password_validation.validate_password(password, user)
        except forms.ValidationError as exc:
            raise forms.ValidationError(exc.messages)

        return password

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

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise forms.ValidationError("Введите логин.")

        if len(username) < 3:
            raise forms.ValidationError("Логин должен содержать не менее 3 символов.")

        if len(username) > 150:
            raise forms.ValidationError("Логин не может быть длиннее 150 символов.")

        if not USERNAME_PATTERN.match(username):
            raise forms.ValidationError(
                "Логин может содержать только буквы, цифры и символы @ . + - _."
            )

        qs = User.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Этот логин уже занят.")

        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return email

        if not EMAIL_PATTERN.match(email):
            raise forms.ValidationError("Введите корректный адрес email.")

        if len(email) > 254:
            raise forms.ValidationError("Email слишком длинный.")

        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Пользователь с таким email уже существует.")

        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return phone

        if not PHONE_PATTERN.match(phone):
            raise forms.ValidationError("Формат телефона должен быть +7 (XXX) XXX-XX-XX.")
        return phone

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if not password:
            return password

        if len(password) < 8:
            raise forms.ValidationError("Пароль должен быть не менее 8 символов.")

        user = self.instance or User(
            username=self.cleaned_data.get("username", ""),
            email=self.cleaned_data.get("email", ""),
        )
        try:
            password_validation.validate_password(password, user)
        except forms.ValidationError as exc:
            raise forms.ValidationError(exc.messages)

        return password

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


