# main/utils.py
"""
Централизованные декораторы для проверки ролей.

Все три декоратора ведут себя одинаково:
- если пользователь не авторизован → отправляем на страницу входа;
- если роль не подходит → рендерим кастомный шаблон 403 напрямую (через render
  с status=403), чтобы страница была видна в том числе в DEBUG-режиме,
  когда Django-шный handler403 не вызывается.

Дополнительно: для клиентских «действий» (`@user_required`) блокируются
небезопасные HTTP-методы (POST/PUT/PATCH/DELETE), если активен один из
«режимов предпросмотра» — администратор в режиме Impersonation или модератор
в режиме клиентского предпросмотра. Это предотвращает создание контента
(бронирований, отзывов и т. п.) от чужого имени.
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import render

# Ключи сессии, указывающие на активный preview-режим.
_IMPERSONATOR_KEY = "impersonator_id"
_MODERATOR_PREVIEW_KEY = "moderator_preview"

# HTTP-методы, которые меняют состояние — именно их запрещаем в preview.
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _forbidden(request, *, message=None):
    """
    Для AJAX-запросов отдаём JSON с 403 — фронт на бронирование/отзыв
    ожидает именно JSON и не умеет парсить HTML. Для обычных запросов
    рендерим полноценную страницу 403.
    """
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": False,
                "ok": False,
                "message": message or "Действие недоступно в режиме предпросмотра.",
            },
            status=403,
        )
    return render(request, "403.html", status=403)


def is_preview_mode(request) -> bool:
    """
    Активен ли у запроса один из режимов «смотрим глазами клиента»:
      * админ через Impersonation (в сессии лежит impersonator_id);
      * модератор через preview (session[moderator_preview]=True).
    """
    session = getattr(request, "session", None)
    if not session:
        return False
    return bool(
        session.get(_IMPERSONATOR_KEY) or session.get(_MODERATOR_PREVIEW_KEY)
    )


def _require_role(check_role, *, block_preview_writes=False):
    """Фабрика декораторов: принимает функцию-предикат (user -> bool)."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = getattr(request, "user", None)
            if not user or not user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not check_role(user):
                return _forbidden(request)
            # В режиме предпросмотра запрещаем ТОЛЬКО мутирующие запросы —
            # чтение клиентских страниц остаётся доступным (это нужно для
            # диагностики самого админа / модератора).
            if (
                block_preview_writes
                and request.method in _UNSAFE_METHODS
                and is_preview_mode(request)
            ):
                return _forbidden(
                    request,
                    message=(
                        "В режиме предпросмотра нельзя выполнять действия "
                        "от имени клиента."
                    ),
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def user_required(view_func):
    """
    Только для клиентов (role == 'user'). Модераторам и админам — 403.
    Используется для страниц клиентского контура: профиль, бронирование,
    создание отзыва. В режиме предпросмотра мутирующие HTTP-методы
    блокируются.
    """
    return _require_role(lambda u: u.is_user(), block_preview_writes=True)(view_func)


def moderator_required(view_func):
    """
    Только для модераторов (role == 'moderator'). Остальным — 403.
    """
    return _require_role(lambda u: u.is_moderator())(view_func)


def admin_required(view_func):
    """
    Только для администраторов (role == 'admin'). Остальным — 403.
    """
    return _require_role(lambda u: u.is_admin())(view_func)
