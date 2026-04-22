"""
Контекст-процессоры приложения main.

Прокидывают в любой шаблон флаги, которые нужны в `base.html`
(и вообще в глобальных UI-компонентах).
"""
from .views import MODERATOR_PREVIEW_KEY


def moderator_preview(request):
    """
    Флаг «модератор включил режим предпросмотра клиентской версии сайта».

    Активен, только если пользователь действительно модератор и в его сессии
    включён флаг. Обычные клиенты и админы никогда не получат True — даже
    если кто-то попытается подделать сессию.
    """
    try:
        user = getattr(request, "user", None)
        active = bool(request.session.get(MODERATOR_PREVIEW_KEY))
    except Exception:
        active = False
        user = None

    if active and user and user.is_authenticated and user.is_moderator():
        return {"is_moderator_preview": True}
    return {"is_moderator_preview": False}
