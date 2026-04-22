from django.shortcuts import render


def custom_page_not_found(request, exception=None):
    """
    Обработчик 404. Подхватывается Django как handler404 при DEBUG=False,
    а также вызывается вручную из `/errors/404/` для превью в DEBUG-режиме.
    """
    return render(request, "404.html", status=404)


def custom_permission_denied(request, exception=None):
    """
    Обработчик 403. Срабатывает на `raise PermissionDenied` при DEBUG=False,
    а декораторы ролей вызывают его напрямую — чтобы работало и в DEBUG.
    """
    return render(request, "403.html", status=403)


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

    last_booking = None

    if request.user.is_authenticated:
        # Получаем последнюю запись пользователя, чтобы достать имя ребенка
        last_booking = request.user.bookings.order_by("-created_at").first()

    return render(
        request,
        "main/index.html",
        {
            "services_list": services_list,
            "last_booking": last_booking,
        },
    )


def why_us(request):
    return render(request, "main/why_us.html")
