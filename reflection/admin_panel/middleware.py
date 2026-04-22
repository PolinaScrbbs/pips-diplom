"""
AuditContextMiddleware — прокидывает текущего пользователя, его IP и
User-Agent в thread-local, чтобы сигналы ORM могли атрибутировать
действия конкретному актору.
"""
import threading

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
