from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from main.utils import moderator_required
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


@moderator_required
def moderator_services_list(request):
    query = request.GET.get('search', '')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    services = Service.objects.all().order_by('-created_at')

    if query:
        services = services.filter(Q(name__icontains=query) | Q(short_description__icontains=query))
    
    if min_price:
        services = services.filter(price__gte=min_price)
    if max_price:
        services = services.filter(price__lte=max_price)

    paginator = Paginator(services, 10) # 10 услуг на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'services/moderator_list.html', {
        'page_obj': page_obj,
        'query': query
    })