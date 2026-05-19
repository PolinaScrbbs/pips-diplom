# users/views.py
import logging

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.core.paginator import Paginator

from main.utils import user_required
from users.forms import LoginForm, RegisterForm
from reviews.forms import ReviewCreateForm

logger = logging.getLogger("app.users")


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            logger.info("New user registered: %s", user.username)
            messages.success(request, "Вы успешно зарегистрировались.")
            return redirect("users:login")
        logger.warning(
            "Registration validation failed: %s",
            form.errors.as_json(ensure_ascii=False),
        )
    else:
        form = RegisterForm()

    return render(request, "users/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            logger.info("User %s logged in (role=%s)", user.username, user.role)
            messages.success(request, "Добро пожаловать!")
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url:
                return redirect(next_url)
            if user.is_admin():
                return redirect("admin_panel:users_list")
            if user.is_moderator():
                return redirect("services:moderator_list")
            return redirect("main:index")
        logger.warning(
            "Login validation failed for username='%s': %s",
            request.POST.get("username", ""),
            form.errors.as_json(ensure_ascii=False),
        )
    else:
        form = LoginForm()

    return render(request, "users/login.html", {"form": form})


def logout_view(request):
    if request.user.is_authenticated:
        logger.info("User %s logged out", request.user.username)
    logout(request)
    return redirect("users:login")


@user_required
def profile_view(request):
    if request.method == "POST":
        # 1. Получаем данные из формы
        new_username = request.POST.get("username")
        new_email = request.POST.get("email")
        new_phone = request.POST.get("phone")

        # 2. Обновляем поля пользователя напрямую
        request.user.username = new_username
        request.user.email = new_email
        request.user.phone = new_phone  # Теперь это поле есть в самой модели User

        # 3. Сохраняем изменения в базе данных
        request.user.save()

        # 4. Перенаправляем обратно в профиль
        return redirect("users:profile")

    bookings_list = request.user.bookings.all().order_by("-created_at")

    # Пагинация: 5 записей на страницу
    paginator = Paginator(bookings_list, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "review_form": ReviewCreateForm(),
    }
    return render(request, "users/profile.html", context)
