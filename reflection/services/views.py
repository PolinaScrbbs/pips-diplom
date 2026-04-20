from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from main.utils import moderator_required
from services.forms import ServiceForm
from .models import Service


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
    search_query = request.GET.get("search", "")
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
        services = services.filter(name__icontains=search_query)
    # ... (логика с ценой из прошлых шагов) ...

    paginator = Paginator(services, 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "services/moderator_list.html",
        {
            "page_obj": page_obj,
            "search_query": search_query,
            "min_price": min_price,
            "max_price": max_price,
            "sort": sort_by,
            "visibility": visibility,  # Не забудьте передать в контекст
        },
    )


@moderator_required
def service_create(request):
    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save()
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
            return JsonResponse({"status": "success"})
        return JsonResponse({"status": "error", "errors": form.errors}, status=400)


@moderator_required
def service_toggle_visibility(request, pk):
    if request.method == "POST":
        service = get_object_or_404(Service, pk=pk)
        service.is_hidden = not service.is_hidden
        service.save()
        return JsonResponse({"status": "success", "is_hidden": service.is_hidden})


@moderator_required  # Если у вас есть такой декоратор
def service_delete(request, pk):
    if request.method == "POST":
        service = get_object_or_404(Service, pk=pk)
        service.delete()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)
