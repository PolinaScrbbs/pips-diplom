import logging
import json
import re
import urllib.request
import urllib.error
from decimal import Decimal, InvalidOperation
import os

from django.http import JsonResponse
from django.db import connection
from django.db.models import Q, Avg, Count
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache

from main.utils import moderator_required
from services.forms import ServiceForm
from .models import Service

logger = logging.getLogger("app.services")

def _ollama_base_url() -> str:
    """
    Base URL для Ollama.

    В Docker `127.0.0.1` указывает на контейнер, поэтому адрес нужно настраивать:
    - Docker Desktop (macOS/Windows): http://host.docker.internal:11434
    - compose-сервис:               http://ollama:11434
    """
    base = (os.getenv("REFLECTION_OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
    # если кто-то указал ".../api" — нормализуем до корня
    if base.endswith("/api"):
        base = base[: -len("/api")]
    return base


def _ollama_explain_keyword(word: str, *, timeout_s: float = 25.0) -> str:
    prompt = (
        "Объясни простыми словами для родителей, что означает термин в контексте детской психологии/развития.\n"
        "Ответ: 1–3 предложения, без списков, без лишних вводных.\n"
        f"Термин: {word}\n"
    )
    model = os.getenv("REFLECTION_LLM_MODEL") or "qwen2.5:7b-instruct"

    # 1) Пробуем /api/generate (старый/простой API)
    payload_generate = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    last_http_error = None
    try:
        req = urllib.request.Request(
            f"{_ollama_base_url()}/api/generate",
            data=json.dumps(payload_generate, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        txt = (data.get("response") or "").strip()
    except urllib.error.HTTPError as e:
        # Некоторые сборки/режимы Ollama не отдают /api/generate → пробуем /api/chat
        if getattr(e, "code", None) != 404:
            raise
        last_http_error = e
        payload_chat = {
            "model": model,
            "stream": False,
            "options": {"temperature": 0.2},
            "messages": [
                {"role": "system", "content": "Ты помощник. Отвечай кратко и по делу."},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            req = urllib.request.Request(
                f"{_ollama_base_url()}/api/chat",
                data=json.dumps(payload_chat, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            msg = (data.get("message") or {}) if isinstance(data, dict) else {}
            txt = (msg.get("content") or "").strip()
        except urllib.error.HTTPError as e2:
            # Если и chat не найден — пробуем OpenAI-совместимый API (/v1).
            if getattr(e2, "code", None) != 404:
                raise
            payload_v1 = {
                "model": model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": "Ты помощник. Отвечай кратко и по делу."},
                    {"role": "user", "content": prompt},
                ],
            }
            req = urllib.request.Request(
                f"{_ollama_base_url()}/v1/chat/completions",
                data=json.dumps(payload_v1, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as e3:
                # Диагностика: /api/tags доступен, а generate/chat/v1 отсутствуют.
                tried = [
                    f"{_ollama_base_url()}/api/generate",
                    f"{_ollama_base_url()}/api/chat",
                    f"{_ollama_base_url()}/v1/chat/completions",
                ]
                tags_status = None
                try:
                    with urllib.request.urlopen(f"{_ollama_base_url()}/api/tags", timeout=timeout_s) as resp:
                        tags_status = getattr(resp, "status", None) or 200
                except Exception:
                    tags_status = None
                msg = (
                    "ollama_endpoints_unavailable: "
                    f"generate=404 chat=404 v1={getattr(e3,'code',None)} tags_status={tags_status} tried={tried}"
                )
                raise urllib.error.HTTPError(e3.url, e3.code, msg, e3.hdrs, e3.fp)
            data = json.loads(raw)
            choices = data.get("choices") or []
            first = choices[0] if choices else {}
            msg = first.get("message") or {}
            txt = (msg.get("content") or "").strip()

    # убираем markdown fences если вдруг есть
    txt = re.sub(r"^```\\w*\\s*|```$", "", txt).strip()
    return txt


def keyword_ask(request):
    word = (request.GET.get("word") or "").strip().lower()
    if not word:
        return JsonResponse({"status": "error", "message": "word is required"}, status=400)
    if len(word) > 80:
        word = word[:80]

    cache_key = f"kw_explain:v1:{word}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse({"status": "success", "word": word, "answer": cached, "cached": True})

    try:
        ans = _ollama_explain_keyword(word)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        # Важно для отладки в Docker: показать, куда ходили.
        urls = [
            f"{_ollama_base_url()}/api/generate",
            f"{_ollama_base_url()}/api/chat",
            f"{_ollama_base_url()}/v1/chat/completions",
        ]
        return JsonResponse(
            {"status": "error", "message": str(e), "ollama_url": urls[0], "ollama_urls_tried": urls},
            status=502,
        )

    cache.set(cache_key, ans, timeout=24 * 60 * 60)
    return JsonResponse({"status": "success", "word": word, "answer": ans, "cached": False})


def services(request):
    services_list = Service.objects.filter(is_hidden=False).order_by("name")

    paginator = Paginator(services_list, 6)
    page = request.GET.get("page", 1)

    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        "page_obj": page_obj,
        "has_more": paginator.num_pages > (page_obj.number if page_obj else 1),
    }
    return render(request, "services/services.html", context)


def load_more_services(request):
    page = request.GET.get("page", 1)
    per_page = 6

    offset = (int(page) - 1) * per_page
    slice_start = offset
    slice_end = offset + per_page

    all_services = list(Service.objects.all().order_by("name"))
    current_page = all_services[slice_start:slice_end]
    has_next = len(all_services) > slice_end

    res = [
        {
            "name": s.name,
            "short_description": s.short_description,
            "duration": s.duration,
            "price": float(s.price) if s.price else None,
            "description": s.description or "",
        }
        for s in current_page
    ]

    return JsonResponse(
        {
            "items": res,
            "has_next": has_next,
        }
    )


def service_detail(request, pk):
    """
    Детальное описание услуги по её первичному ключу (ID).
    """
    service = get_object_or_404(Service, pk=pk)
    return render(request, "services/service_detail.html", {"service": service})


@moderator_required
def moderator_services_list(request):
    search_query = (request.GET.get("search") or "").strip()
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    sort_by = request.GET.get("sort", "-created_at")

    # Новый параметр фильтра: all, visible (default), hidden
    visibility = request.GET.get("visibility", "visible")

    services = Service.objects.all().order_by(sort_by)

    # Фильтр по видимости
    if visibility == "visible":
        services = services.filter(is_hidden=False)
    elif visibility == "hidden":
        services = services.filter(is_hidden=True)
    # если 'all', то ничего не фильтруем

    # Остальные фильтры (поиск, цена...)
    if search_query:
        # В SQLite `icontains`/LOWER() часто не работают корректно для кириллицы.
        # Поэтому для sqlite делаем Unicode-safe фильтрацию через casefold() в Python.
        if connection.vendor == "sqlite":
            q = search_query.casefold()
            services = [s for s in services if q in (s.name or "").casefold()]
        else:
            services = services.filter(name__icontains=search_query)

    # Фильтр по цене (min/max). Работает и для queryset, и для списка (sqlite+python search).
    def _to_decimal(v: str):
        v = (v or "").strip().replace(",", ".")
        if not v:
            return None
        try:
            return Decimal(v)
        except (InvalidOperation, ValueError):
            return None

    min_p = _to_decimal(min_price)
    max_p = _to_decimal(max_price)

    if min_p is not None:
        if isinstance(services, list):
            services = [s for s in services if s.price is not None and s.price >= min_p]
        else:
            services = services.filter(price__gte=min_p)
    if max_p is not None:
        if isinstance(services, list):
            services = [s for s in services if s.price is not None and s.price <= max_p]
        else:
            services = services.filter(price__lte=max_p)

    paginator = Paginator(services, 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    # KPI по всему справочнику услуг (не зависят от текущего фильтра — это общая
    # картинка, так удобнее при принятии решений).
    kpi = Service.objects.aggregate(
        total=Count("id"),
        visible=Count("id", filter=Q(is_hidden=False)),
        hidden=Count("id", filter=Q(is_hidden=True)),
        avg_price=Avg("price"),
    )
    has_filters = bool(search_query or min_price or max_price or visibility != "visible")

    # AJAX: возвращаем только блок результатов (grid + пагинация), без перерисовки страницы.
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string(
            "services/_moderator_list_results.html",
            {
                "page_obj": page_obj,
                "search_query": search_query,
                "min_price": min_price,
                "max_price": max_price,
                "sort": sort_by,
                "visibility": visibility,
                "kpi": kpi,
                "has_filters": has_filters,
            },
            request=request,
        )
        return JsonResponse({"status": "success", "html": html})

    return render(
        request,
        "services/moderator_list.html",
        {
            "page_obj": page_obj,
            "search_query": search_query,
            "min_price": min_price,
            "max_price": max_price,
            "sort": sort_by,
            "visibility": visibility,
            "kpi": kpi,
            "has_filters": has_filters,
        },
    )


@moderator_required
def service_create(request):
    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save()
            logger.info(
                "Moderator %s created service '%s' (id=%s)",
                request.user.username, service.name, service.id,
            )
            return JsonResponse(
                {
                    "status": "success",
                    "message": "Услуга успешно создана!",
                    "service": {"id": service.id, "name": service.name},
                }
            )
        else:
            return JsonResponse({"status": "error", "errors": form.errors}, status=400)
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)


@moderator_required
def service_detail_json(request, pk):
    service = get_object_or_404(Service, pk=pk)
    return JsonResponse(
        {
            "id": service.id,
            "name": service.name,
            "price": service.price,
            "duration": service.duration,
            "short_description": service.short_description,
            "description": service.description,
        }
    )


# Сохранение изменений
@moderator_required
def service_update(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            logger.info(
                "Moderator %s updated service '%s' (id=%s)",
                request.user.username, service.name, service.id,
            )
            return JsonResponse({"status": "success"})
        return JsonResponse({"status": "error", "errors": form.errors}, status=400)


@moderator_required
def service_toggle_visibility(request, pk):
    if request.method == "POST":
        service = get_object_or_404(Service, pk=pk)
        service.is_hidden = not service.is_hidden
        service.save()
        logger.info(
            "Moderator %s %s service '%s' (id=%s)",
            request.user.username,
            "hid" if service.is_hidden else "unhid",
            service.name, service.id,
        )
        return JsonResponse({"status": "success", "is_hidden": service.is_hidden})


@moderator_required  # Если у вас есть такой декоратор
def service_delete(request, pk):
    if request.method == "POST":
        service = get_object_or_404(Service, pk=pk)
        name = service.name
        service.delete()
        logger.warning(
            "Moderator %s deleted service '%s' (id=%s)",
            request.user.username, name, pk,
        )
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)
