# main/utils.py
"""
Централизованные декораторы для проверки ролей.

Все три декоратора ведут себя одинаково:
- если пользователь не авторизован → отправляем на страницу входа;
- если роль не подходит → рендерим кастомный шаблон 403 напрямую (через render
  с status=403), чтобы страница была видна в том числе в DEBUG-режиме,
  когда Django-шный handler403 не вызывается.
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render


def _forbidden(request):
    return render(request, "403.html", status=403)


def _require_role(check_role):
    """Фабрика декораторов: принимает функцию-предикат (user -> bool)."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = getattr(request, "user", None)
            if not user or not user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not check_role(user):
                return _forbidden(request)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def user_required(view_func):
    """
    Только для клиентов (role == 'user'). Модераторам и админам — 403.
    Используется для страниц клиентского контура: профиль, бронирование,
    создание отзыва.
    """
    return _require_role(lambda u: u.is_user())(view_func)


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
