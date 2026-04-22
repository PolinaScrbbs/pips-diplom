"""
AuditContextMiddleware — прокидывает текущего пользователя, его IP и
User-Agent в thread-local, чтобы сигналы ORM могли атрибутировать
действия конкретному актору.

QueryLogMiddleware — принудительно включает `force_debug_cursor` на время
запроса и собирает все выполненные SQL-запросы в in-memory кольцевой буфер.
Пишется только для действий авторизованного админа — чтобы не создавать
overhead в клиентском трафике.
"""
import threading
from django.db import connection

from admin_panel.query_log import query_log

_ctx = threading.local()


def get_audit_context() -> dict:
    return {
        "user": getattr(_ctx, "user", None),
        "ip": getattr(_ctx, "ip", None),
        "user_agent": getattr(_ctx, "user_agent", None),
    }


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _ctx.user = getattr(request, "user", None)
        _ctx.ip = self._client_ip(request)
        _ctx.user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:255]
        try:
            return self.get_response(request)
        finally:
            _ctx.user = None
            _ctx.ip = None
            _ctx.user_agent = None

    @staticmethod
    def _client_ip(request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


# Пути, на которых мы НЕ логируем запросы — иначе страница просмотра
# запросов сама себя будет засорять.
_QL_SKIP_PREFIXES = (
    "/admin-panel/db/queries/",
    "/admin-panel/db/schema/",
    "/static/",
    "/media/",
)


class QueryLogMiddleware:
    """
    Собирает выполненные во время запроса SQL-команды в память.
    Активен только когда `request.user.is_authenticated and is_admin()`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""
        if any(path.startswith(p) for p in _QL_SKIP_PREFIXES):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return self.get_response(request)
        # only for admin
        if not getattr(user, "is_admin", None) or not user.is_admin():
            return self.get_response(request)

        prev_debug = connection.force_debug_cursor
        connection.force_debug_cursor = True
        before = len(connection.queries_log)
        try:
            response = self.get_response(request)
        finally:
            connection.force_debug_cursor = prev_debug

        try:
            new = list(connection.queries_log)[before:]
        except Exception:
            new = []

        status = getattr(response, "status_code", None) if response is not None else None
        username = getattr(user, "username", "") or ""
        for q in new:
            try:
                duration_ms = float(q.get("time", 0)) * 1000.0
            except (TypeError, ValueError):
                duration_ms = 0.0
            query_log.record(
                sql=q.get("sql", ""),
                duration_ms=duration_ms,
                path=path,
                method=request.method,
                user=username,
                status=status,
            )

        return response
