"""
main/middleware.py

NavigationLoggingMiddleware — логирует переходы пользователей по страницам.
Попадает в системный лог-терминал в виде:

    2026-04-22 13:40:12 | INFO    | app.nav            | [guest]           GET /services/  →  Услуги  (200)
    2026-04-22 13:40:30 | INFO    | app.nav            | [alice/user]      GET /users/profile/  →  Личный кабинет  (200)
    2026-04-22 13:40:42 | WARN    | app.nav            | [alice/user]      GET /admin-panel/  →  Админ-панель (403 Forbidden)

Фильтры:
  - только HTML-запросы (пропускаем favicon, статику, media, AJAX-поллинг логов);
  - метод GET (POST-действия уже логируются в соответствующих views);
  - не пишем сам /admin-panel/logs/stream/, иначе получим обратную связь.
"""

import logging

logger = logging.getLogger("app.nav")


# URL-имена, которые мы хотим видеть «по-человечески» вместо сырого пути.
_PAGE_NAMES = {
    "main:index": "Главная",
    "main:why_us": "Почему мы",
    "services:services": "Услуги",
    "services:service_detail": "Детали услуги",
    "services:moderator_list": "Панель модератора — услуги",
    "reviews:reviews": "Отзывы",
    "reviews:moderator_reviews": "Панель модератора — отзывы",
    "users:login": "Страница входа",
    "users:register": "Страница регистрации",
    "users:logout": "Выход из аккаунта",
    "users:profile": "Личный кабинет",
    "admin_panel:users_list": "Админ-панель — пользователи",
    "admin_panel:logs": "Админ-панель — логи",
}

# Префиксы путей, которые мы игнорируем (статика, ajax-поллинг и т.д.)
_IGNORED_PREFIXES = (
    "/static/",
    "/media/",
    "/favicon.ico",
    "/admin/jsi18n/",
    "/admin-panel/logs/stream/",
    "/services/load-more/",
)


class NavigationLoggingMiddleware:
    """Записывает каждую осмысленную навигацию пользователя в лог."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._log(request, response)
        except Exception:  # noqa: BLE001
            # Никогда не валим запрос из-за ошибки логирования.
            logger.exception("Navigation logging failed")
        return response

    def _log(self, request, response):
        if request.method != "GET":
            return

        path = request.path
        if any(path.startswith(p) for p in _IGNORED_PREFIXES):
            return

        # Пропускаем нетекстовые ответы (картинки, JSON-API, файлы на скачивание).
        ctype = response.get("Content-Type", "")
        status = response.status_code
        is_html = ctype.startswith("text/html")
        is_redirect = 300 <= status < 400
        if not (is_html or is_redirect):
            return

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            who = f"{user.username}/{user.role}"
        else:
            who = "guest"

        # Человекочитаемое имя страницы по URL name, если есть.
        match = getattr(request, "resolver_match", None)
        if match and match.view_name in _PAGE_NAMES:
            page = _PAGE_NAMES[match.view_name]
        elif match and match.view_name:
            page = match.view_name
        else:
            page = path

        # 4xx / 5xx — отдельный уровень лога, чтобы сразу видеть попытки обхода прав.
        if status >= 500:
            level = logging.ERROR
        elif status >= 400:
            level = logging.WARNING
        else:
            level = logging.INFO

        status_note = ""
        if status == 403:
            status_note = " Forbidden"
        elif status == 404:
            status_note = " Not Found"
        elif is_redirect:
            status_note = f" → {response.get('Location', '')}"

        logger.log(
            level,
            "[%s] GET %s → %s (%d%s)",
            who,
            path,
            page,
            status,
            status_note,
        )
