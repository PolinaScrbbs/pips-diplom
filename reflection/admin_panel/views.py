import logging
import re
from datetime import date as date_type, datetime

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q, Value
from django.db.models.functions import Replace
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date

from admin_panel.decorators import admin_required
from admin_panel.forms import UserCreateForm, UserUpdateForm
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
