from users.models import User


def impersonation(request):
    """
    Прокидывает в шаблоны инфу об активной сессии impersonation:
      is_impersonating: bool
      impersonator_username: str | None
    """
    impersonator_id = request.session.get("impersonator_id") if hasattr(request, "session") else None
    if not impersonator_id:
        return {"is_impersonating": False, "impersonator_username": None}

    username = request.session.get("impersonator_username")
    if not username:
        try:
            username = User.objects.get(pk=impersonator_id).username
        except User.DoesNotExist:
            username = None
    return {
        "is_impersonating": True,
        "impersonator_username": username,
    }
