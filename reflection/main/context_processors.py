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


def preview_mode(request):
    """
    Общий флаг «сейчас пользователь действует в режиме предпросмотра»:
      * админ в сессии Impersonation;
      * модератор в режиме клиентского предпросмотра.

    Используется в шаблонах, чтобы прятать/блокировать кнопки, открывающие
    формы записи и создания отзыва от чужого имени.
    """
    session = getattr(request, "session", None)
    if not session:
        return {"is_preview_mode": False}

    is_imp = bool(session.get("impersonator_id"))
    is_mod_preview = False
    user = getattr(request, "user", None)
    if (
        user
        and user.is_authenticated
        and getattr(user, "is_moderator", lambda: False)()
        and session.get(MODERATOR_PREVIEW_KEY)
    ):
        is_mod_preview = True

    return {"is_preview_mode": is_imp or is_mod_preview}
