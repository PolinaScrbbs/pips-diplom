from django.core.paginator import Paginator
from django.db.models import Q, Value
from django.db.models.functions import Replace
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date

from admin_panel.decorators import admin_required
from admin_panel.forms import UserCreateForm, UserUpdateForm
from users.models import User


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

    return JsonResponse(
        {
            "status": "success",
            "message": f"Пользователь «{username}» удалён.",
            "user": {"id": pk},
        }
    )
