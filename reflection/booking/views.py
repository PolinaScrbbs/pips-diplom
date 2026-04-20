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
        # Это спасет, если JS сработал дважды или пользователь быстро нажал кнопку
        last_booking_exists = Booking.objects.filter(
            user=request.user, created_at__gt=timezone.now() - timedelta(seconds=5)
        ).exists()

        if last_booking_exists:
            # Если дубль пойман, возвращаем успех (чтобы фронтенд показал галочку),
            # но в базе ничего не создаем.
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True})
            return redirect(request.POST.get("next", "main:index"))

        # 2. ОБРАБОТКА ФОРМЫ
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.save()

            # Если это AJAX-запрос (от fetch в JS)
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True})

            # Если это обычная отправка формы (fallback)
            return redirect(request.POST.get("next", "main:index"))

        else:
            # Если форма невалидна
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "errors": form.errors}, status=400
                )
            # В случае обычной ошибки просто возвращаем на главную (или где была форма)
            return redirect(request.POST.get("next", "main:index"))

    # Если зашли через GET — просто отправляем на главную
    return redirect("main:index")
