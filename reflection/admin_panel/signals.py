"""
Auto-аудит: pre_save/post_save/post_delete для набора отслеживаемых моделей.

Состояние "до" кэшируется на pre_save, в post_save считается diff, на
post_delete — создаётся запись-удаление. Отслеживаются только поля из
TRACKED_MODELS — это защищает от логирования служебных изменений
(например, last_login у User).
"""
import threading
from decimal import Decimal

from django.apps import apps
from django.db.models.signals import post_delete, post_save, pre_save

from admin_panel.middleware import get_audit_context

TRACKED_MODELS = {
    "users.User": ["username", "email", "role", "is_active", "first_name", "last_name", "phone"],
    "services.Service": ["name", "price", "is_hidden", "duration", "short_description"],
    "reviews.Review": ["rating", "text", "relation"],
    "booking.Booking": ["child_name", "parent_name", "phone", "comment"],
}

_pre_cache = threading.local()


def _label(instance) -> str:
    return f"{instance._meta.app_label}.{instance.__class__.__name__}"


def _entity_type(instance) -> str:
    return instance.__class__.__name__.lower()


def _snapshot(instance, fields: list) -> dict:
    """Снимок интересующих полей с нормализацией значений в JSON-совместимые типы."""
    out = {}
    for f in fields:
        v = getattr(instance, f, None)
        if isinstance(v, Decimal):
            v = str(v)
        elif hasattr(v, "isoformat"):
            v = v.isoformat()
        out[f] = v
    return out


def _get_cache() -> dict:
    if not hasattr(_pre_cache, "data"):
        _pre_cache.data = {}
    return _pre_cache.data


def _pre_save_handler(sender, instance, **kwargs):
    label = _label(instance)
    if label not in TRACKED_MODELS or not instance.pk:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    _get_cache()[(label, instance.pk)] = _snapshot(previous, TRACKED_MODELS[label])


def _post_save_handler(sender, instance, created, **kwargs):
    label = _label(instance)
    if label not in TRACKED_MODELS:
        return
    fields = TRACKED_MODELS[label]
    current = _snapshot(instance, fields)

    if created:
        changes = {f: {"before": None, "after": current.get(f)} for f in fields}
        action = "create"
    else:
        before = _get_cache().pop((label, instance.pk), {})
        changes = {}
        for f in fields:
            b, a = before.get(f), current.get(f)
            if b != a:
                changes[f] = {"before": b, "after": a}
        if not changes:
            return
        action = "update"

    _write(action, instance, changes)


def _post_delete_handler(sender, instance, **kwargs):
    label = _label(instance)
    if label not in TRACKED_MODELS:
        return
    fields = TRACKED_MODELS[label]
    snapshot = _snapshot(instance, fields)
    _write("delete", instance, {f: {"before": v, "after": None} for f, v in snapshot.items()})


def _write(action: str, instance, changes: dict):
    from admin_panel.models import AuditLog

    ctx = get_audit_context()
    user = ctx["user"]
    if user is not None and getattr(user, "is_authenticated", False):
        actor_obj = user
        actor_username = user.username
        actor_role = getattr(user, "role", "")
    else:
        actor_obj = None
        actor_username = "system"
        actor_role = ""

    AuditLog.objects.create(
        actor=actor_obj,
        actor_username=actor_username,
        actor_role=actor_role,
        action=action,
        entity_type=_entity_type(instance),
        entity_id=getattr(instance, "pk", None),
        entity_repr=str(instance)[:255],
        changes=changes,
        ip_address=ctx.get("ip"),
        user_agent=(ctx.get("user_agent") or "")[:255],
    )


def write_manual(action: str, *, actor, entity_type: str, entity_id=None, entity_repr="", changes=None, request=None):
    """Ручная запись — например, для impersonation, когда CRUD не срабатывает."""
    from admin_panel.models import AuditLog

    ctx = get_audit_context()
    ip = ctx.get("ip")
    ua = ctx.get("user_agent")
    if request is not None:
        ip = ip or request.META.get("REMOTE_ADDR")
        ua = ua or (request.META.get("HTTP_USER_AGENT") or "")[:255]

    AuditLog.objects.create(
        actor=actor if getattr(actor, "pk", None) else None,
        actor_username=getattr(actor, "username", "") or "system",
        actor_role=getattr(actor, "role", ""),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_repr=entity_repr[:255],
        changes=changes or {},
        ip_address=ip,
        user_agent=(ua or "")[:255],
    )


def register():
    """Вызывается из AppConfig.ready() после загрузки всех приложений."""
    for label in TRACKED_MODELS:
        try:
            model = apps.get_model(label)
        except LookupError:
            continue
        uid = label.replace(".", "_")
        pre_save.connect(_pre_save_handler, sender=model, dispatch_uid=f"audit_pre_{uid}")
        post_save.connect(_post_save_handler, sender=model, dispatch_uid=f"audit_post_{uid}")
        post_delete.connect(_post_delete_handler, sender=model, dispatch_uid=f"audit_del_{uid}")
