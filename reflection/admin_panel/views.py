import logging
import re
import time
import json
from datetime import date as date_type, datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum, Value
from django.db.models.functions import Replace, TruncDate
from django.contrib.auth import login
from django.http import FileResponse, Http404, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from booking.models import Booking
from reviews.models import Review
from services.models import Service

from admin_panel.db_inspector import get_schema_overview
from admin_panel.decorators import admin_required
from admin_panel.forms import UserCreateForm, UserUpdateForm
from admin_panel.insights import (
    generate_stats_insights,
    generate_stats_insights_compat,
    limit_items,
    mask_text,
    normalize_sql,
    ollama_stream_response,
    sanitize_stats_data,
    _llm_prompt_stats,
)
from admin_panel.models import AuditLog
from admin_panel.query_log import query_log
from admin_panel.signals import write_manual as audit_write
from users.models import User

logger = logging.getLogger("app.admin")


def _deny_other_admin_editing(request, target_user: User):
    if target_user.role == User.ADMIN and target_user.pk != request.user.pk:
        return JsonResponse(
            {"status": "error", "message": "Нельзя изменять других администраторов."},
            status=403,
        )
    return None


@admin_required
def users_list(request):
    search_query = request.GET.get("search", "")
    role = request.GET.get("role", "non_admin")  # non_admin|all|user|moderator|admin
    status = request.GET.get("status", "active")  # active|inactive|all
    sort_by = request.GET.get("sort", "-date_joined")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    users_qs = User.objects.all().order_by(sort_by)

    if status == "active":
        users_qs = users_qs.filter(is_active=True)
    elif status == "inactive":
        users_qs = users_qs.filter(is_active=False)

    if role == "non_admin":
        users_qs = users_qs.filter(role__in=[User.USER, User.MODERATOR])
    elif role != "all":
        users_qs = users_qs.filter(role=role)

    if date_from:
        parsed = parse_date(date_from)
        if parsed:
            users_qs = users_qs.filter(date_joined__date__gte=parsed)

    if date_to:
        parsed = parse_date(date_to)
        if parsed:
            users_qs = users_qs.filter(date_joined__date__lte=parsed)

    if search_query:
        digits_query = "".join(ch for ch in search_query if ch.isdigit())

        base_q = Q(username__icontains=search_query) | Q(email__icontains=search_query)

        # По телефону ищем и "как есть", и в нормализованном виде (только цифры),
        # чтобы совпадали форматы вроде "+7 (951) 317-12-14" и "79513171214".
        phone_q = Q(phone__icontains=search_query)
        if digits_query:
            users_qs = users_qs.annotate(
                phone_digits=Replace(
                    Replace(
                        Replace(
                            Replace(
                                Replace(
                                    Replace("phone", Value("+"), Value("")),
                                    Value(" "),
                                    Value(""),
                                ),
                                Value("("),
                                Value(""),
                            ),
                            Value(")"),
                            Value(""),
                        ),
                        Value("-"),
                        Value(""),
                    ),
                    Value("\u00a0"),  # неразрывный пробел
                    Value(""),
                )
            )
            phone_q = phone_q | Q(phone_digits__icontains=digits_query)

        users_qs = users_qs.filter(base_q | phone_q)

    paginator = Paginator(users_qs, 4)
    page_obj = paginator.get_page(request.GET.get("page"))
    empty_rows = range(max(0, 4 - len(page_obj.object_list)))

    return render(
        request,
        "admin_panel/users_list.html",
        {
            "page_obj": page_obj,
            "empty_rows": empty_rows,
            "create_form": UserCreateForm(),
            "search_query": search_query,
            "role": role,
            "status": status,
            "sort": sort_by,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


@admin_required
def user_create(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    form = UserCreateForm(request.POST)
    if form.is_valid():
        user = form.save()
        logger.info(
            "Admin %s created user %s (role=%s)",
            request.user.username, user.username, user.role,
        )
        return JsonResponse(
            {
                "status": "success",
                "message": "Пользователь создан.",
                "user": {"id": user.id, "username": user.username},
            }
        )

    return JsonResponse({"status": "error", "errors": form.errors}, status=400)


@admin_required
def user_detail_json(request, pk: int):
    user = get_object_or_404(User, pk=pk)
    denied = _deny_other_admin_editing(request, user)
    if denied:
        return denied
    return JsonResponse(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email or "",
            "phone": user.phone or "",
            "role": user.role,
        }
    )


@admin_required
def user_update(request, pk: int):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    user = get_object_or_404(User, pk=pk)
    denied = _deny_other_admin_editing(request, user)
    if denied:
        return denied
    form = UserUpdateForm(request.POST, instance=user)
    if form.is_valid():
        saved = form.save()
        logger.info(
            "Admin %s updated user %s (id=%s)",
            request.user.username, saved.username, saved.id,
        )
        return JsonResponse(
            {
                "status": "success",
                "message": "Пользователь обновлён.",
                "user": {"id": saved.id, "username": saved.username},
            }
        )

    return JsonResponse({"status": "error", "errors": form.errors}, status=400)


@admin_required
def user_toggle_active(request, pk: int):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    user = get_object_or_404(User, pk=pk)
    denied = _deny_other_admin_editing(request, user)
    if denied:
        return denied

    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    logger.warning(
        "Admin %s %s user %s (id=%s)",
        request.user.username,
        "activated" if user.is_active else "deactivated",
        user.username, user.id,
    )

    return JsonResponse(
        {
            "status": "success",
            "user": {"id": user.id, "is_active": user.is_active},
        }
    )


@admin_required
def user_delete(request, pk: int):
    """
    Удаление пользователя. Правила:
    - метод только POST (без CSRF GET-запросов);
    - нельзя удалить самого себя;
    - нельзя удалить другого администратора.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    user = get_object_or_404(User, pk=pk)

    if user.pk == request.user.pk:
        return JsonResponse(
            {"status": "error", "message": "Нельзя удалить собственный аккаунт."},
            status=403,
        )

    if user.role == User.ADMIN:
        return JsonResponse(
            {"status": "error", "message": "Нельзя удалять других администраторов."},
            status=403,
        )

    username = user.username
    user.delete()
    logger.warning(
        "Admin %s deleted user %s (id=%s)",
        request.user.username, username, pk,
    )

    return JsonResponse(
        {
            "status": "success",
            "message": f"Пользователь «{username}» удалён.",
            "user": {"id": pk},
        }
    )


# ---------------------------------------------------------------------------
# Системные логи
# Файлы лежат в media/logs/YYYY-MM/DD.log. В терминал отдаём последние 100
# строк, полный файл за день можно запросить явно или скачать.
# ---------------------------------------------------------------------------
_LOG_LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s\|\s"
    r"(?P<level>\S+)\s+\|\s"
    r"(?P<source>[^|]+?)\s+\|\s"
    r"(?P<message>.*)$"
)

# Извлечение имени пользователя из сообщений app.nav / app.admin / и др.
_USER_TAG_RE = re.compile(r"\[(?P<username>[^/\]]+)/(?P<role>[^\]]+)\]")

_LOGS_DEFAULT_TAIL = 100
_LOGS_MAX_LINES = 2000  # hard-limit на объём ответа даже без tail


def _file_for_date(d: date_type):
    """Путь к файлу-логу конкретной даты (не проверяет существование)."""
    return settings.APP_LOG_DIR / d.strftime("%Y-%m") / (d.strftime("%d") + ".log")


def _parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _available_dates():
    """Список дат YYYY-MM-DD (по убыванию), для которых есть файлы."""
    root = settings.APP_LOG_DIR
    if not root.exists():
        return []
    found = []
    for month_dir in root.iterdir():
        if not month_dir.is_dir():
            continue
        for file in month_dir.iterdir():
            if file.suffix != ".log":
                continue
            iso = f"{month_dir.name}-{file.stem}"
            if _parse_date(iso):
                found.append(iso)
    return sorted(found, reverse=True)


def _read_file_lines(path):
    """Читаем ВЕСЬ файл построчно. Файл за день обычно небольшой (сотни KB)."""
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _parse_log_line(line: str) -> dict:
    m = _LOG_LINE_RE.match(line)
    if not m:
        return {
            "ts": "", "level": "RAW", "source": "",
            "message": line, "user": "",
        }
    msg = m.group("message")
    user_m = _USER_TAG_RE.search(msg)
    return {
        "ts": m.group("ts"),
        "level": m.group("level"),
        "source": m.group("source").strip(),
        "message": msg,
        "user": user_m.group("username") if user_m else "",
    }


def _extract_time(ts: str) -> str:
    """'2026-04-22 13:17:36' → '13:17:36'; пусто если формат сломан."""
    parts = ts.split(" ", 1)
    return parts[1] if len(parts) == 2 else ""


@admin_required
def logs_page(request):
    """Страница системных логов с терминальным интерфейсом."""
    return render(
        request,
        "admin_panel/logs.html",
        {"today": date_type.today().isoformat()},
    )


@admin_required
def logs_stream(request):
    """
    AJAX-поток логов за выбранную дату. Параметры:
      date        YYYY-MM-DD (по умолчанию — сегодня),
      level       INFO | WARNING | ERROR | DEBUG | ALL,
      q           подстрока поиска по сообщению и источнику,
      user        имя пользователя (точное, из тега [name/role]),
      from_time   HH:MM — нижняя граница времени (включительно),
      to_time     HH:MM — верхняя граница времени (включительно),
      tail        'y' | 'n' — ограничивать ли последними 100 строками (по умолчанию y).
    """
    date_str = request.GET.get("date") or date_type.today().isoformat()
    d = _parse_date(date_str)
    if d is None:
        return JsonResponse({"error": "Invalid date"}, status=400)

    level = (request.GET.get("level") or "ALL").upper().strip()
    query = (request.GET.get("q") or "").strip().lower()
    user_filter = (request.GET.get("user") or "").strip()
    from_time = (request.GET.get("from_time") or "").strip()
    to_time = (request.GET.get("to_time") or "").strip()
    tail_mode = (request.GET.get("tail") or "y").lower() != "n"

    path = _file_for_date(d)
    raw_lines = _read_file_lines(path)
    parsed = [_parse_log_line(ln) for ln in raw_lines if ln.strip()]

    if level and level != "ALL":
        parsed = [p for p in parsed if p["level"] == level]
    if query:
        parsed = [
            p for p in parsed
            if query in p["message"].lower() or query in p["source"].lower()
        ]
    if user_filter:
        parsed = [p for p in parsed if p["user"] == user_filter]
    if from_time:
        parsed = [p for p in parsed if _extract_time(p["ts"]) >= from_time]
    if to_time:
        parsed = [p for p in parsed if _extract_time(p["ts"]) <= to_time]

    total = len(parsed)
    if tail_mode and total > _LOGS_DEFAULT_TAIL:
        parsed = parsed[-_LOGS_DEFAULT_TAIL:]
    elif total > _LOGS_MAX_LINES:
        parsed = parsed[-_LOGS_MAX_LINES:]

    return JsonResponse(
        {
            "lines": parsed,
            "returned": len(parsed),
            "total": total,
            "truncated": total > len(parsed),
            "date": d.isoformat(),
            "is_today": d == date_type.today(),
            "file_exists": path.exists(),
        }
    )


@admin_required
def logs_dates(request):
    """Список всех дней, за которые есть логи (для выпадайки)."""
    return JsonResponse({"dates": _available_dates(), "today": date_type.today().isoformat()})


@admin_required
def logs_users(request):
    """
    Последние 10 пользователей, засветившихся в логах за выбранную дату
    (по умолчанию — сегодня). Порядок — от самого недавнего к более раннему.
    Возвращаем также их роль (берём ту, что была в последнем упоминании).
    """
    date_str = request.GET.get("date") or date_type.today().isoformat()
    d = _parse_date(date_str)
    if d is None:
        return JsonResponse({"users": []})

    path = _file_for_date(d)
    if not path.exists():
        return JsonResponse({"users": []})

    seen: dict[str, str] = {}
    order: list[str] = []
    for ln in reversed(_read_file_lines(path)):
        m = _USER_TAG_RE.search(ln)
        if not m:
            continue
        username = m.group("username")
        if username in seen:
            continue
        seen[username] = m.group("role")
        order.append(username)
        if len(order) >= 10:
            break

    users = [{"username": u, "role": seen[u]} for u in order]
    return JsonResponse({"users": users})


@admin_required
def logs_clear(request):
    """
    Обнуляем лог за указанную дату (по умолчанию — сегодня).
    В лог добавляется запись о том, кто это сделал.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    date_str = request.POST.get("date") or date_type.today().isoformat()
    d = _parse_date(date_str)
    if d is None:
        return JsonResponse({"status": "error", "message": "Invalid date"}, status=400)

    path = _file_for_date(d)
    if path.exists():
        path.write_text("", encoding="utf-8")
    logger.warning("Admin %s cleared logs for %s", request.user.username, d.isoformat())
    return JsonResponse({"status": "success", "message": f"Лог за {d.isoformat()} очищен."})


@admin_required
def logs_download(request):
    """Скачать лог за конкретную дату (?date=YYYY-MM-DD, по умолчанию — сегодня)."""
    date_str = request.GET.get("date") or date_type.today().isoformat()
    d = _parse_date(date_str)
    if d is None:
        raise Http404("Invalid date")
    path = _file_for_date(d)
    if not path.exists():
        raise Http404("Лог за указанную дату не найден.")
    logger.info("Admin %s downloaded logs for %s", request.user.username, d.isoformat())
    return FileResponse(
        path.open("rb"),
        as_attachment=True,
        filename=f"app-{d.isoformat()}.log",
    )


# ---------------------------------------------------------------------------
# Статистика — сводные графики по пользователям, услугам, записям и отзывам.
# ---------------------------------------------------------------------------
def _build_date_series(qs_map: dict, days: int):
    """
    qs_map: {date_obj: value} — произвольный словарь с датами из БД.
    Возвращает два массива [labels_iso], [values] — ровно за `days` дней
    подряд, от (сегодня - days + 1) до сегодня, включая дни без событий (0).
    """
    today = timezone.localdate()
    labels, values = [], []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        labels.append(d.isoformat())
        values.append(float(qs_map.get(d, 0) or 0))
    return labels, values


def _counts_by_date(queryset, field: str, days: int):
    """Группировка по дате (без времени) с TruncDate — SQLite-совместимо."""
    since = timezone.now() - timedelta(days=days - 1)
    rows = (
        queryset.filter(**{f"{field}__gte": since})
        .annotate(d=TruncDate(field))
        .values("d")
        .annotate(n=Count("id"))
    )
    return {r["d"]: r["n"] for r in rows if r["d"] is not None}


def _sum_by_date(queryset, field: str, sum_field: str, days: int):
    since = timezone.now() - timedelta(days=days - 1)
    rows = (
        queryset.filter(**{f"{field}__gte": since})
        .annotate(d=TruncDate(field))
        .values("d")
        .annotate(s=Sum(sum_field))
    )
    return {r["d"]: r["s"] for r in rows if r["d"] is not None}


@admin_required
def stats_page(request):
    """HTML-страница статистики (сами данные грузятся JSON-endpoint'ом)."""
    return render(request, "admin_panel/stats.html")


@admin_required
def stats_data(request):
    """
    JSON со всеми показателями для дашборда. Диапазон — 30 дней по умолчанию,
    можно переопределить через ?days=<7|30|90>.
    """
    try:
        days = int(request.GET.get("days") or 30)
    except (TypeError, ValueError):
        days = 30
    days = max(7, min(365, days))

    today = timezone.localdate()
    period_start = today - timedelta(days=days - 1)

    # --- KPI -----------------------------------------------------------------
    total_users = User.objects.count()
    users_by_role = {
        row["role"]: row["n"]
        for row in User.objects.values("role").annotate(n=Count("id"))
    }
    active_services = Service.objects.filter(is_hidden=False).count()
    total_services = Service.objects.count()
    total_bookings = Booking.objects.count()
    bookings_in_period = Booking.objects.filter(created_at__date__gte=period_start).count()
    avg_rating = Review.objects.aggregate(avg=Avg("rating"))["avg"]
    total_reviews = Review.objects.count()

    # --- Series --------------------------------------------------------------
    signups_labels, signups = _build_date_series(
        _counts_by_date(User.objects.all(), "date_joined", days),
        days,
    )
    _, bookings_series = _build_date_series(
        _counts_by_date(Booking.objects.all(), "created_at", days),
        days,
    )

    # Выручка = сумма цен услуг по забронированным записям (агрегируем
    # отдельно, чтобы не тянуть сервис в каждую строку).
    revenue_map = {}
    revenue_rows = (
        Booking.objects.filter(created_at__date__gte=period_start)
        .annotate(d=TruncDate("created_at"))
        .values("d")
        .annotate(s=Sum("service__price"))
    )
    for r in revenue_rows:
        if r["d"] is not None:
            revenue_map[r["d"]] = r["s"]
    _, revenue_series = _build_date_series(revenue_map, days)
    total_revenue = sum(revenue_series)

    # --- Топ услуг -----------------------------------------------------------
    top_services = list(
        Service.objects.annotate(c=Count("bookings"))
        .order_by("-c", "name")[:8]
        .values("name", "c")
    )

    # --- Распределение оценок ------------------------------------------------
    rating_rows = Review.objects.values("rating").annotate(c=Count("id"))
    rating_counts = [0, 0, 0, 0, 0]
    for r in rating_rows:
        if 1 <= r["rating"] <= 5:
            rating_counts[r["rating"] - 1] = r["c"]

    # --- Активность по дню недели (ПН..ВС) -----------------------------------
    # SQLite не умеет нативно дни недели: считаем в Python, это дёшево.
    weekday_counts = [0] * 7
    for b in Booking.objects.filter(created_at__date__gte=period_start).values_list(
        "created_at", flat=True
    ):
        local_day = timezone.localtime(b).weekday()
        weekday_counts[local_day] += 1

    # --- Активность по часу дня ---------------------------------------------
    hour_counts = [0] * 24
    for b in Booking.objects.filter(created_at__date__gte=period_start).values_list(
        "created_at", flat=True
    ):
        hour_counts[timezone.localtime(b).hour] += 1

    # --- Топ активных клиентов ----------------------------------------------
    top_clients = list(
        User.objects.filter(role=User.USER)
        .annotate(c=Count("bookings"))
        .filter(c__gt=0)
        .order_by("-c", "username")[:5]
        .values("username", "c")
    )

    return JsonResponse({
        "days": days,
        "kpi": {
            "total_users": total_users,
            "users_by_role": {
                "user": users_by_role.get(User.USER, 0),
                "moderator": users_by_role.get(User.MODERATOR, 0),
                "admin": users_by_role.get(User.ADMIN, 0),
            },
            "active_services": active_services,
            "total_services": total_services,
            "total_bookings": total_bookings,
            "bookings_in_period": bookings_in_period,
            "avg_rating": round(avg_rating, 2) if avg_rating is not None else None,
            "total_reviews": total_reviews,
            "total_revenue": float(total_revenue or 0),
        },
        "series": {
            "labels": signups_labels,
            "signups": signups,
            "bookings": bookings_series,
            "revenue": revenue_series,
        },
        "top_services": top_services,
        "rating_counts": rating_counts,
        "weekday_counts": weekday_counts,
        "hour_counts": hour_counts,
        "top_clients": top_clients,
    })


_STATS_INSIGHTS_CACHE_TTL_S = 10 * 60  # 10 минут
_STATS_INSIGHTS_TIMEOUT_S = 180.0  # По запросу: без лимитов, ждём дольше


@admin_required
def stats_insights(request):
    """
    JSON-инсайты поверх `stats_data`. Параметры:
      days   — 7|30|90 (как у stats_data; ограничение 7..365),
      force  — 1 чтобы игнорировать кэш.

    Контракт ответа (успех):
      {
        "status": "success",
        "cached": true|false,
        "days": 30,
        "mode": "heuristic",
        "generated_at": "2026-05-01T18:00:00+00:00",
        "input_digest": "a1b2c3d4e5f6g7h8",
        "insights": {
          "summary": "...",
          "changes": [{"text": "...", "metric": "...", "new": 1, "old": 2, "pct": -50.0, "unit": ""}],
          "anomalies": ["..."],
          "recommendations": ["..."],
          "numbers_used": {...},
          "input_days": 30
        }
      }
    """
    try:
        days = int(request.GET.get("days") or 30)
    except (TypeError, ValueError):
        days = 30
    days = max(7, min(365, days))

    force = (request.GET.get("force") or "").strip() in ("1", "true", "yes", "y")
    cache_key = f"admin_panel:stats_insights:v1:days={days}"

    if not force:
        cached = cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return JsonResponse(cached)

    # Собираем базовую статистику так же, как для графиков.
    # Важно: не делаем доп. запросов к БД сверх уже существующих в stats_data().
    started = time.monotonic()
    stats_json = json.loads(stats_data(request).content.decode("utf-8"))
    # generate_stats_insights now uses local LLM (Ollama) if available, else fallback.
    result = generate_stats_insights(stats_json, prefer_llm=True)
    elapsed_ms = int((time.monotonic() - started) * 1000)

    payload = {
        "status": "success",
        "cached": False,
        "days": days,
        "mode": result.mode,
        "generated_at": result.generated_at,
        "input_digest": result.input_digest,
        "insights": result.insights,
        "meta": {
            "timeout_s": _STATS_INSIGHTS_TIMEOUT_S,
            "elapsed_ms": elapsed_ms,
            "cache_ttl_s": _STATS_INSIGHTS_CACHE_TTL_S,
            "llm_error": result.llm_error,
        },
    }
    cache.set(cache_key, payload, timeout=_STATS_INSIGHTS_CACHE_TTL_S)
    return JsonResponse(payload)


@admin_required
def stats_insights_stream(request):
    """
    SSE-стрим прогресса для LLM-инсайтов.
    События:
      - progress: {"pct": int, "label": str}
      - result:   <полный JSON ответа как в stats_insights>
    """
    try:
        days = int(request.GET.get("days") or 30)
    except (TypeError, ValueError):
        days = 30
    days = max(7, min(365, days))

    force = (request.GET.get("force") or "").strip() in ("1", "true", "yes", "y")
    cache_key = f"admin_panel:stats_insights:v1:days={days}"

    if not force:
        cached = cache.get(cache_key)
        if cached:
            cached2 = dict(cached)
            cached2["cached"] = True
            cached_json = json.dumps(cached2, ensure_ascii=False)

            def cached_gen():
                yield "event: progress\ndata: {\"pct\":100,\"label\":\"Готово (кэш)\"}\n\n"
                yield f"event: result\ndata: {cached_json}\n\n"

            resp = StreamingHttpResponse(cached_gen(), content_type="text/event-stream")
            resp["Cache-Control"] = "no-cache"
            return resp

    started = time.monotonic()
    stats_json = json.loads(stats_data(request).content.decode("utf-8"))
    safe = sanitize_stats_data(stats_json)

    series = safe.get("series") or {}
    signups = list(series.get("signups") or [])
    bookings = list(series.get("bookings") or [])
    revenue = list(series.get("revenue") or [])
    window = 7
    numbers_used = {
        "signups_7d": sum(signups[-window:]) if len(signups) >= window else sum(signups),
        "signups_prev_7d": sum(signups[-2 * window:-window]) if len(signups) >= 2 * window else 0.0,
        "bookings_7d": sum(bookings[-window:]) if len(bookings) >= window else sum(bookings),
        "bookings_prev_7d": sum(bookings[-2 * window:-window]) if len(bookings) >= 2 * window else 0.0,
        "revenue_7d": sum(revenue[-window:]) if len(revenue) >= window else sum(revenue),
        "revenue_prev_7d": sum(revenue[-2 * window:-window]) if len(revenue) >= 2 * window else 0.0,
    }
    full_payload = dict(safe)
    full_payload["numbers_used"] = numbers_used

    model = "qwen2.5:7b-instruct"
    timeout_s = _STATS_INSIGHTS_TIMEOUT_S
    try:
        import os

        model = os.getenv("REFLECTION_LLM_MODEL") or model
        timeout_s = float(os.getenv("REFLECTION_LLM_TIMEOUT_S") or timeout_s)
    except Exception:
        pass

    prompt = _llm_prompt_stats(compact=full_payload)

    def sse_pack(event: str, data_obj) -> str:
        return f"event: {event}\ndata: {json.dumps(data_obj, ensure_ascii=False)}\n\n"

    def _validate_llm_insights(obj) -> bool:
        if not isinstance(obj, dict):
            return False
        if not isinstance(obj.get("summary"), str):
            return False
        recs = obj.get("recommendations")
        if not isinstance(recs, list) or not all(isinstance(x, str) for x in recs):
            return False
        changes = obj.get("changes")
        if not isinstance(changes, list):
            return False
        anomalies = obj.get("anomalies")
        if anomalies is not None and not isinstance(anomalies, list):
            return False
        return True

    def gen():
        yield sse_pack("progress", {"pct": 1, "label": "Подключение к модели…"})
        buf = []
        chars_seen = 0
        last_sent_pct = 1
        try:
            for chunk in ollama_stream_response(model=model, prompt=prompt, timeout_s=timeout_s):
                frag = chunk.get("response") or ""
                if frag:
                    buf.append(frag)
                    chars_seen += len(frag)
                    # Прогресс по факту генерации: растём до 95% пока done=false.
                    pct = min(95, 5 + int((chars_seen / (chars_seen + 2000.0)) * 90))
                    if pct > last_sent_pct:
                        last_sent_pct = pct
                        yield sse_pack("progress", {"pct": pct, "label": "Модель генерирует ответ…"})
                if chunk.get("done"):
                    break

            text = "".join(buf).strip()
            try:
                llm_json = json.loads(text)
            except json.JSONDecodeError:
                m = re.search(r"\{[\s\S]*\}", text)
                llm_json = json.loads(m.group(0)) if m else {}

            llm_error = None
            if not _validate_llm_insights(llm_json):
                llm_error = "llm_output_invalid_contract"
                llm_json = generate_stats_insights(stats_json, prefer_llm=False).insights

            elapsed_ms = int((time.monotonic() - started) * 1000)
            payload = {
                "status": "success",
                "cached": False,
                "days": days,
                "mode": "llm" if llm_error is None else "heuristic",
                "generated_at": datetime.now(dt_timezone.utc).isoformat(timespec="seconds"),
                "input_digest": "",
                "insights": llm_json if isinstance(llm_json, dict) else {"summary": str(llm_json)},
                "meta": {
                    "timeout_s": timeout_s,
                    "elapsed_ms": elapsed_ms,
                    "cache_ttl_s": _STATS_INSIGHTS_CACHE_TTL_S,
                    "llm_error": llm_error,
                },
            }
            cache.set(cache_key, payload, timeout=_STATS_INSIGHTS_CACHE_TTL_S)
            yield sse_pack("progress", {"pct": 100, "label": "Готово"})
            yield sse_pack("result", payload)
        except Exception as e:  # noqa: BLE001
            yield sse_pack("progress", {"pct": 100, "label": "Ошибка"})
            yield sse_pack("result", {"status": "error", "message": str(e)})

    resp = StreamingHttpResponse(gen(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    return resp


# ---------------------------------------------------------------------------
# Аудит-журнал — лента действий персонала над ключевыми сущностями.
# ---------------------------------------------------------------------------
_AUDIT_PAGE_SIZE = 30
_ENTITY_LABELS = {
    "user": "Пользователь",
    "service": "Услуга",
    "review": "Отзыв",
    "booking": "Запись",
}


def _serialize_audit(row: AuditLog) -> dict:
    return {
        "id": row.id,
        "created_at": timezone.localtime(row.created_at).isoformat(timespec="seconds"),
        "actor": row.actor_username or "system",
        "actor_role": row.actor_role or "",
        "action": row.action,
        "entity_type": row.entity_type,
        "entity_label": _ENTITY_LABELS.get(row.entity_type, row.entity_type),
        "entity_id": row.entity_id,
        "entity_repr": row.entity_repr,
        "ip_address": row.ip_address or "",
        "changed_fields": sorted(list((row.changes or {}).keys())),
    }


@admin_required
def audit_page(request):
    return render(request, "admin_panel/audit.html")


def _page_range_window(current: int, total: int, side: int = 2) -> list:
    """
    Возвращает список номеров страниц + сентинелов-многоточий для компактной
    пагинации вида: 1 … 4 5 [6] 7 8 … 20.
    Сентинел для «…» = 0 (в шаблоне просто не-ссылка).
    """
    if total <= 1:
        return [1] if total == 1 else []

    pages = set()
    pages.add(1)
    pages.add(total)
    for p in range(current - side, current + side + 1):
        if 1 <= p <= total:
            pages.add(p)

    ordered = sorted(pages)
    result = []
    prev = 0
    for p in ordered:
        if prev and p - prev > 1:
            result.append(0)  # ellipsis
        result.append(p)
        prev = p
    return result


@admin_required
def audit_data(request):
    """Возвращает страницу аудита с применением фильтров."""
    qs = AuditLog.objects.all().select_related("actor")

    action = (request.GET.get("action") or "").strip()
    if action and action != "ALL":
        qs = qs.filter(action=action)

    entity = (request.GET.get("entity") or "").strip()
    if entity and entity != "ALL":
        qs = qs.filter(entity_type=entity)

    actor = (request.GET.get("actor") or "").strip()
    if actor:
        qs = qs.filter(actor_username__icontains=actor)

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(entity_repr__icontains=q) | Q(actor_username__icontains=q))

    date_from = request.GET.get("from")
    if date_from:
        d = parse_date(date_from) or parse_datetime(date_from)
        if d:
            qs = qs.filter(created_at__date__gte=d if hasattr(d, "date") is False else d.date())

    date_to = request.GET.get("to")
    if date_to:
        d = parse_date(date_to) or parse_datetime(date_to)
        if d:
            qs = qs.filter(created_at__date__lte=d if hasattr(d, "date") is False else d.date())

    paginator = Paginator(qs, _AUDIT_PAGE_SIZE)
    try:
        page_num = max(int(request.GET.get("page", 1)), 1)
    except (TypeError, ValueError):
        page_num = 1
    page_num = min(page_num, paginator.num_pages or 1)
    page = paginator.page(page_num) if paginator.count else None

    rows = list(page.object_list) if page else []
    return JsonResponse({
        "entries": [_serialize_audit(r) for r in rows],
        "page": page_num,
        "page_size": _AUDIT_PAGE_SIZE,
        "total_pages": paginator.num_pages if paginator.count else 0,
        "total": paginator.count,
        "has_prev": bool(page and page.has_previous()),
        "has_next": bool(page and page.has_next()),
        "page_range": _page_range_window(page_num, paginator.num_pages if paginator.count else 0),
        "index_from": ((page_num - 1) * _AUDIT_PAGE_SIZE + 1) if paginator.count else 0,
        "index_to": ((page_num - 1) * _AUDIT_PAGE_SIZE + len(rows)) if paginator.count else 0,
    })


@admin_required
def audit_detail(request, pk: int):
    row = get_object_or_404(AuditLog, pk=pk)
    data = _serialize_audit(row)
    data["changes"] = row.changes or {}
    data["user_agent"] = row.user_agent or ""
    return JsonResponse(data)


@admin_required
def audit_filters(request):
    """Справочники для выпадаек: уникальные акторы и типы сущностей."""
    actors = list(
        AuditLog.objects.exclude(actor_username="")
        .order_by("actor_username")
        .values_list("actor_username", flat=True)
        .distinct()[:50]
    )
    entities = list(
        AuditLog.objects.exclude(entity_type="")
        .order_by()
        .values_list("entity_type", flat=True)
        .distinct()
    )
    entities = [{"value": e, "label": _ENTITY_LABELS.get(e, e)} for e in sorted(entities)]
    return JsonResponse({
        "actors": actors,
        "entities": entities,
        "actions": [{"value": code, "label": label} for code, label in AuditLog.ACTION_CHOICES],
    })


# ---------------------------------------------------------------------------
# Impersonation — «войти за пользователя».
# ---------------------------------------------------------------------------
_IMPERSONATE_KEY = "impersonator_id"


@admin_required
def impersonate_user(request, pk: int):
    """
    Начинает сессию impersonation: админ логинится как другой пользователь.
    Ограничения: админ не может impersonate самого себя или другого админа.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST allowed."}, status=405)

    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        return JsonResponse({"status": "error", "message": "Нельзя impersonate самого себя."}, status=400)
    if target.role == User.ADMIN:
        return JsonResponse({"status": "error", "message": "Нельзя impersonate администратора."}, status=403)
    if not target.is_active:
        return JsonResponse({"status": "error", "message": "Пользователь деактивирован."}, status=400)

    original_id = request.user.pk
    original_username = request.user.username
    original_role = request.user.role

    audit_write(
        AuditLog.ACTION_IMPERSONATE,
        actor=request.user,
        entity_type="user",
        entity_id=target.pk,
        entity_repr=f"{target.username} ({target.get_role_display()})",
        changes={"target": target.username, "from_user": original_username},
        request=request,
    )

    login(request, target)
    request.session[_IMPERSONATE_KEY] = original_id
    request.session["impersonator_username"] = original_username
    request.session["impersonator_role"] = original_role

    logger.warning(
        "Admin %s started impersonation of %s", original_username, target.username
    )

    redirect_to = reverse("main:index")
    if target.is_user():
        redirect_to = reverse("users:profile")
    elif target.is_moderator():
        redirect_to = reverse("services:moderator_list")

    return JsonResponse({"status": "success", "redirect": redirect_to})


def stop_impersonation(request):
    """
    Выход из режима impersonation. Доступен любому авторизованному, если в
    сессии есть impersonator_id — потому что «перевоплощённый» пользователь
    сейчас технически и есть request.user.
    """
    original_id = request.session.pop(_IMPERSONATE_KEY, None)
    original_username = request.session.pop("impersonator_username", None)
    request.session.pop("impersonator_role", None)

    if not original_id:
        return redirect("main:index")

    try:
        original = User.objects.get(pk=original_id, is_active=True)
    except User.DoesNotExist:
        return redirect("main:index")

    was_as = request.user.username if request.user.is_authenticated else "?"
    audit_write(
        AuditLog.ACTION_STOP_IMPERSONATE,
        actor=original,
        entity_type="user",
        entity_id=request.user.pk if request.user.is_authenticated else None,
        entity_repr=f"{was_as}",
        changes={"from_user": was_as, "back_to": original.username},
        request=request,
    )

    login(request, original)
    logger.warning(
        "Admin %s stopped impersonation (was %s)", original.username, original_username or was_as
    )
    return redirect("admin_panel:users_list")


# ---------------------------------------------------------------------------
# DB Inspector — структура БД + последние SQL-запросы.
# ---------------------------------------------------------------------------
@admin_required
def db_page(request):
    return render(request, "admin_panel/db.html")


@admin_required
def db_schema(request):
    return JsonResponse(get_schema_overview())


@admin_required
def db_queries(request):
    try:
        since_id = int(request.GET.get("since", "")) if request.GET.get("since") else None
    except ValueError:
        since_id = None
    try:
        limit = max(1, min(int(request.GET.get("limit", 200)), 500))
    except (TypeError, ValueError):
        limit = 200
    items = query_log.recent(since_id=since_id, limit=limit)
    return JsonResponse({
        "queries": items,
        "stats": query_log.stats(),
    })


@admin_required
def db_queries_clear(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST allowed."}, status=405)
    query_log.clear()
    logger.info("Admin %s cleared query log", request.user.username)
    return JsonResponse({"status": "success"})


# ---------------------------------------------------------------------------
# Weekly extension: Daily brief + Reviews insights (scaffolding).
# ---------------------------------------------------------------------------

_DAILY_BRIEF_CACHE_TTL_S = 5 * 60
_DAILY_BRIEF_MAX_LOG_LINES = 60
_DAILY_BRIEF_MAX_AUDIT = 30


@admin_required
def daily_brief(request):
    """
    MVP на 1 неделю: daily brief = stats + ERROR logs + audit highlights.
    Сейчас без LLM: отдаём структурированный JSON (чтобы легко подключить LLM позже).

    Параметры:
      days   — период для stats (7..365), по умолчанию 30
      date   — дата логов YYYY-MM-DD (по умолчанию сегодня)
      force  — 1 чтобы игнорировать кэш
    """
    try:
        days = int(request.GET.get("days") or 30)
    except (TypeError, ValueError):
        days = 30
    days = max(7, min(365, days))
    force = (request.GET.get("force") or "").strip() in ("1", "true", "yes", "y")

    date_str = request.GET.get("date") or date_type.today().isoformat()
    cache_key = f"admin_panel:daily_brief:v1:days={days}:date={date_str}"
    if not force:
        cached = cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return JsonResponse(cached)

    # 1) Stats (safe aggregates)
    stats_json = json.loads(stats_data(request).content.decode("utf-8"))
    safe_stats = generate_stats_insights(stats_json).insights  # already sanitized via sanitize_stats_data

    # 2) ERROR logs only (safe masked messages)
    d = _parse_date(date_str)
    raw_lines = []
    if d is not None:
        path = _file_for_date(d)
        parsed = [_parse_log_line(ln) for ln in _read_file_lines(path) if ln.strip()]
        parsed = [p for p in parsed if p.get("level") == "ERROR"]
        # tail-mode for brief
        if len(parsed) > _LOGS_DEFAULT_TAIL:
            parsed = parsed[-_LOGS_DEFAULT_TAIL:]
        raw_lines = parsed
    safe_lines = []
    for row in raw_lines:
        if not isinstance(row, dict):
            continue
        safe_lines.append({
            "ts": row.get("ts") or "",
            "level": row.get("level") or "",
            "source": row.get("source") or "",
            "message": mask_text(row.get("message") or "", max_len=400),
        })
    safe_lines = limit_items(safe_lines, max_items=_DAILY_BRIEF_MAX_LOG_LINES)

    # 3) Audit highlights (no ip/user_agent/changes values)
    audit_qs = AuditLog.objects.all().order_by("-created_at")[:_DAILY_BRIEF_MAX_AUDIT]
    audit_entries = []
    for row in audit_qs:
        audit_entries.append({
            "created_at": timezone.localtime(row.created_at).isoformat(timespec="seconds"),
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "entity_repr": mask_text(row.entity_repr or "", max_len=140),
            "actor_role": row.actor_role or "",
            "changed_fields": sorted(list((row.changes or {}).keys())),
        })

    payload = {
        "status": "success",
        "cached": False,
        "days": days,
        "date": date_str,
        "brief": {
            "stats_insights": safe_stats,
            "errors": {
                "returned": len(safe_lines),
                "lines": safe_lines,
            },
            "audit": audit_entries,
        },
        "meta": {
            "cache_ttl_s": _DAILY_BRIEF_CACHE_TTL_S,
            "limits": {
                "max_log_lines": _DAILY_BRIEF_MAX_LOG_LINES,
                "max_audit": _DAILY_BRIEF_MAX_AUDIT,
            },
        },
    }
    cache.set(cache_key, payload, timeout=_DAILY_BRIEF_CACHE_TTL_S)
    return JsonResponse(payload)


_REVIEWS_INSIGHTS_CACHE_TTL_S = 10 * 60
_REVIEWS_INSIGHTS_MAX_ITEMS = 200
_REVIEWS_INSIGHTS_MAX_LEN = 700


@admin_required
def reviews_insights(request):
    """
    MVP на 1 неделю: инсайты по отзывам (темы/негатив).
    Сейчас без LLM: отдаём подготовленный безопасный payload + простую сводку.

    Параметры:
      limit — сколько отзывов анализировать (1..200), по умолчанию 120
      only_negative — 1 чтобы брать rating<=2 (по умолчанию 1)
      force — 1 чтобы игнорировать кэш
    """
    try:
        limit = int(request.GET.get("limit") or 120)
    except (TypeError, ValueError):
        limit = 120
    limit = max(1, min(_REVIEWS_INSIGHTS_MAX_ITEMS, limit))
    only_negative = (request.GET.get("only_negative") or "1").strip() in ("1", "true", "yes", "y")
    force = (request.GET.get("force") or "").strip() in ("1", "true", "yes", "y")

    cache_key = f"admin_panel:reviews_insights:v1:limit={limit}:neg={int(only_negative)}"
    if not force:
        cached = cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return JsonResponse(cached)

    qs = Review.objects.all().order_by("-created_at")
    if only_negative:
        qs = qs.filter(rating__lte=2)
    rows = list(qs.values("rating", "text", "created_at")[:limit])

    texts = []
    for r in rows:
        texts.append({
            "rating": int(r.get("rating") or 0),
            "created_at": timezone.localtime(r["created_at"]).isoformat(timespec="seconds") if r.get("created_at") else "",
            "text": mask_text(r.get("text") or "", max_len=_REVIEWS_INSIGHTS_MAX_LEN),
        })

    # Простая “тематика” без ML: частотные слова (очень грубо, но демонстрационно).
    # LLM можно подключить позже, используя texts[] как safe input.
    stop = set([
        "и","в","во","на","по","что","это","не","я","мы","вы","он","она","они","а","но","или",
        "с","со","к","ко","у","за","от","до","для","как","же","то","так","бы","были","было",
        "очень","просто","только","ещё","еще","уже","нет","да","все","всё",
    ])
    freq = {}
    for t in texts:
        words = re.findall(r"[A-Za-zА-Яа-яЁё]{3,}", t["text"].lower())
        for w in words:
            if w in stop:
                continue
            freq[w] = freq.get(w, 0) + 1
    top_terms = sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:12]

    payload = {
        "status": "success",
        "cached": False,
        "only_negative": only_negative,
        "input": {
            "count": len(texts),
            "items": texts,
        },
        "summary": {
            "top_terms": [{"term": k, "count": v} for k, v in top_terms],
            "note": "Это простая эвристика. Для диплома можно заменить на LLM/кластеризацию, сохранив тот же безопасный вход.",
        },
        "meta": {
            "cache_ttl_s": _REVIEWS_INSIGHTS_CACHE_TTL_S,
            "limits": {
                "max_items": _REVIEWS_INSIGHTS_MAX_ITEMS,
                "max_len": _REVIEWS_INSIGHTS_MAX_LEN,
            },
        },
    }
    cache.set(cache_key, payload, timeout=_REVIEWS_INSIGHTS_CACHE_TTL_S)
    return JsonResponse(payload)
