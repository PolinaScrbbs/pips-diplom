from django.shortcuts import render
from services.models import Service


def index(request):
    services_list = [
        {
            "title": "Детская психология",
            "icon": "bi-emoji-smile",
            "text": "Тревожность, страхи, трудности в школе и дома.",
        },
        {
            "title": "Семейная терапия",
            "icon": "bi-people",
            "text": "Конфликты, адаптация к разводу или переезду.",
        },
        {
            "title": "Помощь школьникам",
            "icon": "bi-book",
            "text": "Мотивация, выбор профессии, отношения со сверстниками.",
        },
        {
            "title": "Развивающие группы",
            "icon": "bi-controller",
            "text": "Развитие эмоционального интеллекта и навыков общения.",
        },
        {
            "title": "Для родителей",
            "icon": "bi-heart-pulse",
            "text": "Помощь в понимании поведения и борьба с выгоранием.",
        },
        {
            "title": "Диагностика",
            "icon": "bi-search",
            "text": "Комплексное обследование и сопровождение в лечении.",
        },
    ]

    services = Service.objects.all()
    last_booking = None

    if request.user.is_authenticated:
        # Получаем последнюю запись пользователя, чтобы достать имя ребенка
        last_booking = request.user.bookings.order_by("-created_at").first()

    return render(
        request,
        "main/index.html",
        {
            "services_list": services_list,
            "services": services,
            "last_booking": last_booking,
        },
    )


def why_us(request):
    return render(request, "main/why_us.html")
