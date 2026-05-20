import logging

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .utils import moderator_required

logger = logging.getLogger("app")

# Ключ сессии для режима «предпросмотра» клиентской версии сайта модератором.
# Храним отдельно от impersonation — это простой UI-флаг, без подмены request.user.
MODERATOR_PREVIEW_KEY = "moderator_preview"


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


def favicon(request):
    """
    Serve a tiny SVG favicon for `/favicon.ico`.
    We keep it inline to avoid committing binary `.ico` files.
    """
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#245633"/>
      <stop offset="1" stop-color="#4a7c59"/>
    </linearGradient>
  </defs>
  <rect x="6" y="6" width="52" height="52" rx="14" fill="url(#g)"/>
  <path d="M33 16c-5 6-12 12-12 20 0 7 5 12 12 12s12-5 12-12c0-8-7-14-12-20z"
        fill="rgba(255,255,255,0.92)"/>
  <path d="M32 26c-2 4-5 7-5 11 0 3 2 5 5 5s5-2 5-5c0-4-3-7-5-11z"
        fill="rgba(36,86,51,0.35)"/>
</svg>
"""
    return HttpResponse(svg, content_type="image/svg+xml")


# ---------------------------------------------------------------------------
# Режим «предпросмотра клиентской версии сайта» для модератора.
#
# Аналог impersonation у админа, но упрощённый: request.user не подменяется
# (модератор остаётся модератором на уровне прав), меняется только внешний
# вид базового шаблона — навбар становится клиентским, а сверху висит
# баннер с кнопкой выхода из режима. Состояние хранится в сессии.
# ---------------------------------------------------------------------------


@require_POST
@moderator_required
def start_moderator_preview(request):
    """Включает режим предпросмотра и отправляет модератора на главную."""
    request.session[MODERATOR_PREVIEW_KEY] = True
    logger.info("Moderator %s started client preview", request.user.username)
    return redirect("main:index")


@require_POST
@moderator_required
def stop_moderator_preview(request):
    """Выключает режим предпросмотра. Доступен всем, у кого он активен в сессии."""
    was_active = request.session.pop(MODERATOR_PREVIEW_KEY, False)
    if was_active and request.user.is_authenticated:
        logger.info("Moderator %s stopped client preview", request.user.username)
    # Возвращаем модератора в его рабочую область.
    if request.user.is_authenticated and request.user.is_moderator():
        return redirect("services:moderator_list")
    return redirect("main:index")
