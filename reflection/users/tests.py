from django.test import TestCase
from django.core.exceptions import ValidationError
from users.models import User
from users.forms import RegisterForm, ProfileForm
from admin_panel.forms import UserCreateForm, UserUpdateForm
from booking.forms import BookingForm
from services.forms import ServiceForm
from reviews.forms import ReviewCreateForm
from services.models import Service


class FormValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="existing_user",
            email="existing@example.com",
            phone="+7 (999) 999-99-99",
            role=User.USER
        )
        self.service = Service.objects.create(
            name="Консультация",
            short_description="Короткое описание",
            description="Полное описание",
            duration="60 мин",
            price=1500.00
        )

    def test_profile_form_valid(self):
        form = ProfileForm(
            data={"username": "valid_user", "email": "valid@example.com", "phone": "+7 (123) 456-78-90"},
            instance=self.user
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_profile_form_invalid_username(self):
        # Username too short
        form = ProfileForm(data={"username": "ab", "email": "valid@example.com", "phone": ""}, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

        # Username already taken
        other_user = User.objects.create_user(username="other", email="other@example.com")
        form = ProfileForm(data={"username": "other", "email": "valid@example.com", "phone": ""}, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_profile_form_invalid_phone(self):
        # Invalid format
        form = ProfileForm(data={"username": "valid_user", "email": "valid@example.com", "phone": "12345"}, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_admin_user_create_form_valid(self):
        form = UserCreateForm(data={
            "username": "new_admin_user",
            "email": "new_admin@example.com",
            "phone": "+7 (999) 111-22-33",
            "role": User.USER,
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!"
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_admin_user_create_form_weak_password(self):
        # Weak password like "1"
        form = UserCreateForm(data={
            "username": "new_admin_user",
            "email": "new_admin@example.com",
            "phone": "+7 (999) 111-22-33",
            "role": User.USER,
            "password1": "1",
            "password2": "1"
        })
        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)

    def test_admin_user_update_form_valid(self):
        form = UserUpdateForm(
            data={
                "username": "existing_user",
                "email": "updated@example.com",
                "phone": "+7 (999) 999-99-99",
                "role": User.USER,
                "password1": "",
                "password2": ""
            },
            instance=self.user
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_admin_user_update_form_weak_password(self):
        # Editing user to set weak password "1"
        form = UserUpdateForm(
            data={
                "username": "existing_user",
                "email": "existing@example.com",
                "phone": "+7 (999) 999-99-99",
                "role": User.USER,
                "password1": "1",
                "password2": "1"
            },
            instance=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)

    def test_booking_form_valid(self):
        form = BookingForm(data={
            "child_name": "Иван",
            "parent_name": "Петр",
            "phone": "+7 (999) 999-99-99",
            "service": self.service.id,
            "comment": "Ждем занятия"
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_booking_form_invalid_names(self):
        # Special characters in name
        form = BookingForm(data={
            "child_name": "Иван123",
            "parent_name": "Петр",
            "phone": "+7 (999) 999-99-99",
            "service": self.service.id
        })
        self.assertFalse(form.is_valid())
        self.assertIn("child_name", form.errors)

    def test_service_form_invalid_price(self):
        # Negative price
        form = ServiceForm(data={
            "name": "Новая услуга",
            "short_description": "Описание",
            "price": -100.00
        })
        self.assertFalse(form.is_valid())
        self.assertIn("price", form.errors)

    def test_review_form_invalid_text(self):
        # Text too short
        form = ReviewCreateForm(data={
            "rating": 5,
            "relation": "Мама",
            "text": "Супер"
        })
        self.assertFalse(form.is_valid())
        self.assertIn("text", form.errors)
