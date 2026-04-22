"""
Интроспекция структуры БД через Django ORM.
Не лезем напрямую в sqlite_master / pg_catalog — всё, что нужно, отдаёт
`apps.get_models()` + `model._meta`. Результат — чистый JSON-готовый dict
для фронтенда.
"""
from django.apps import apps
from django.db import connection


def _field_info(field) -> dict:
    """Сводная инфа по полю для рендера карточки таблицы."""
    info = {
        "name": field.name,
        "type": field.get_internal_type(),
        "null": bool(getattr(field, "null", False)),
        "blank": bool(getattr(field, "blank", False)),
        "primary_key": bool(getattr(field, "primary_key", False)),
        "unique": bool(getattr(field, "unique", False)),
        "db_index": bool(getattr(field, "db_index", False)),
        "max_length": getattr(field, "max_length", None),
        "default": _safe_default(field),
        "help_text": str(getattr(field, "help_text", "") or "")[:160],
        "fk": None,
        "fk_table": None,
        "relation": None,
        "choices": None,
    }

    rel = getattr(field, "remote_field", None)
    if rel is not None and getattr(rel, "model", None):
        related = rel.model
        info["fk"] = related._meta.label
        info["fk_table"] = related._meta.db_table
        if field.many_to_one:
            info["relation"] = "many_to_one"
        elif field.one_to_one:
            info["relation"] = "one_to_one"
        elif field.many_to_many:
            info["relation"] = "many_to_many"
            info["type"] = "ManyToMany"

    choices = getattr(field, "choices", None)
    if choices:
        info["choices"] = len(choices)

    return info


def _safe_default(field) -> str:
    """Делает default JSON-safe: callables превращаем в строку типа."""
    from django.db.models import NOT_PROVIDED
    default = getattr(field, "default", NOT_PROVIDED)
    if default is NOT_PROVIDED:
        return ""
    if callable(default):
        return f"{getattr(default, '__name__', 'callable')}()"
    try:
        return str(default)[:60]
    except Exception:
        return ""


def _row_count(model) -> int | None:
    """Быстрый COUNT(*) по таблице. None если не смогли."""
    try:
        return model.objects.count()
    except Exception:
        return None


def _relations_map() -> list:
    """Все FK/M2M связи в проекте (from → to)."""
    rels = []
    for model in apps.get_models():
        for f in model._meta.get_fields():
            if not getattr(f, "concrete", False):
                continue
            rel = getattr(f, "remote_field", None)
            if not rel or not getattr(rel, "model", None):
                continue
            if f.many_to_one or f.one_to_one or f.many_to_many:
                rels.append({
                    "from_model": model._meta.label,
                    "from_table": model._meta.db_table,
                    "field": f.name,
                    "to_model": rel.model._meta.label,
                    "to_table": rel.model._meta.db_table,
                    "kind": (
                        "O2O" if f.one_to_one
                        else "M2M" if f.many_to_many
                        else "FK"
                    ),
                })
    return rels


def get_schema_overview() -> dict:
    """Полная сводка: таблицы (с полями, count), связи, итоговая статистика."""
    tables = []
    for model in apps.get_models():
        meta = model._meta
        fields = [_field_info(f) for f in meta.get_fields() if getattr(f, "concrete", False)]
        tables.append({
            "label": meta.label,
            "app": meta.app_label,
            "model": model.__name__,
            "table": meta.db_table,
            "verbose": str(meta.verbose_name),
            "verbose_plural": str(meta.verbose_name_plural),
            "rows": _row_count(model),
            "field_count": len(fields),
            "fields": fields,
            "managed": bool(meta.managed),
        })

    # стабильный порядок: сначала наши приложения, потом встроенные
    local_apps = {"users", "services", "booking", "reviews", "admin_panel", "main"}
    tables.sort(key=lambda t: (0 if t["app"] in local_apps else 1, t["app"], t["model"]))

    relations = _relations_map()
    total_rows = sum((t["rows"] or 0) for t in tables)

    return {
        "tables": tables,
        "relations": relations,
        "summary": {
            "table_count": len(tables),
            "relation_count": len(relations),
            "total_rows": total_rows,
            "engine": connection.vendor,
            "database": str(connection.settings_dict.get("NAME", "") or ""),
        },
    }
