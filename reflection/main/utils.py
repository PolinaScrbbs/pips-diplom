# main/utils.py
from django.core.exceptions import PermissionDenied

def moderator_required(view_func):
    def _wrapped_view_request(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_moderator):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view_request