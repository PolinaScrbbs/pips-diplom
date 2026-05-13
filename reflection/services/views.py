import logging
import json
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
from main.ollama_utils import ollama_base_url, ollama_endpoint_chain, ollama_keyword_text_with_fallback
from services.forms import ServiceForm
from .models import Service

logger = logging.getLogger("app.services")


def _ollama_keyword_timeout_s() -> float:
    try:
        t = float(os.getenv("REFLECTION_LLM_TIMEOUT_S") or "60")
    except ValueError:
        t = 60.0
    return min(max(t, 15.0), 300.0)


def _ollama_explain_keyword(word: str, *, timeout_s: float | None = None) -> str:
    if timeout_s is None:
        timeout_s = _ollama_keyword_timeout_s()
    prompt = (
        "Объясни простыми словами для родителей, что означает термин в контексте детской психологии/развития.\n"
        "Ответ: 1–3 предложения, без списков, без лишних вводных.\n"
        f"Термин: {word}\n"
    )
    model = os.getenv("REFLECTION_LLM_MODEL") or "qwen2.5:7b-instruct"
    return ollama_keyword_text_with_fallback(model=model, prompt=prompt, timeout_s=timeout_s)


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
    except Exception as e:
        # Не HTTP 502: иначе fetch падает без текста; отдаём JSON с объяснением (Ollama недоступен, таймаут и т.д.).
        logger.warning("keyword_ask LLM failed: word=%r err=%s", word, e)
        chain = [{"label": lbl, "base_url": u} for lbl, u in ollama_endpoint_chain()]
        return JsonResponse(
            {
                "status": "error",
                "message": str(e),
                "ollama_base": ollama_base_url(),
                "ollama_chain": chain,
            },
            status=200,
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
