# booking/views.py
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .forms import BookingForm
from .models import Booking


@login_required(login_url="users:login")
def create_booking(request):
    if request.method == "POST":
        # 1. ЗАЩИТА ОТ ДУБЛИКАТОВ (АНТИ-СПАМ)
        # Проверяем, не создавал ли этот же пользователь запись в последние 5 секунд
        last_booking_exists = Booking.objects.filter(
            user=request.user, created_at__gt=timezone.now() - timedelta(seconds=5)
        ).exists()

        if last_booking_exists:
            # Если дубль пойман, возвращаем успех для фронтенда, но ничего не создаем
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True})
            return redirect(request.POST.get("next", "main:index"))

        # 2. ОБРАБОТКА ФОРМЫ
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user

            # АВТО-ОБНОВЛЕНИЕ ТЕЛЕФОНА В ПРОФИЛЕ
            # Берем телефон из проверенных данных формы
            phone_from_form = form.cleaned_data.get("phone")

            # Если у текущего юзера поле phone пустое, а в форме оно заполнено
            if not request.user.phone and phone_from_form:
                request.user.phone = phone_from_form
                # Сохраняем только поле телефона, чтобы не задеть другие данные
                request.user.save(update_fields=["phone"])

            booking.save()

            # Ответ для AJAX-запроса (fetch)
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True})

            # Обычный редирект для стандартной отправки формы
            return redirect(request.POST.get("next", "main:index"))

        else:
            # Если форма не прошла валидацию
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "errors": form.errors}, status=400
                )
            return redirect(request.POST.get("next", "main:index"))

    # Если GET-запрос — отправляем на главную
    return redirect("main:index")
