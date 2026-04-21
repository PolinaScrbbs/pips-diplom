from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden


def admin_required(view_func):
    """
    Требует авторизацию и роль администратора (users.User.role == "admin").
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        is_admin = getattr(user, "is_admin", None)
        if callable(is_admin) and user.is_admin():
            return view_func(request, *args, **kwargs)

        return HttpResponseForbidden("Доступ запрещён")

    return _wrapped
