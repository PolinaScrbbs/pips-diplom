from django.core.paginator import Paginator
from django.db.models import Q, Value
from django.db.models.functions import Replace
from django.shortcuts import render
from django.utils.dateparse import parse_date

from admin_panel.decorators import admin_required
from users.models import User


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

    return render(
        request,
        "admin_panel/users_list.html",
        {
            "page_obj": page_obj,
            "search_query": search_query,
            "role": role,
            "status": status,
            "sort": sort_by,
            "date_from": date_from,
            "date_to": date_to,
        },
    )
