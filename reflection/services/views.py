from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Service


def services(request):
    services_list = Service.objects.all().order_by("name")

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
    return render(request, 'services/service_detail.html', {'service': service})