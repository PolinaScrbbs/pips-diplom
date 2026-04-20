# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from users.forms import LoginForm, RegisterForm
from reviews.forms import ReviewCreateForm


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Вы успешно зарегистрировались.")
            return redirect("users:login")
    else:
        form = RegisterForm()

    return render(request, "users/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                messages.success(request, "Добро пожаловать!")
                return redirect("reviews:reviews")  # или куда тебе удобнее
            else:
                messages.error(request, "Неверный логин или пароль.")
    else:
        form = LoginForm()

    return render(request, "users/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("users:login")


@login_required(login_url="users:login")
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
