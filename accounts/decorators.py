from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """
    Allow only logged-in users whose role is in `roles`.

    Logged-out visitors are sent to the login page; logged-in users with the
    wrong role get a 403 page, so one role can never open another role's pages.
    """

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


owner_required = role_required("OWNER")
admin_required = role_required("ADMIN")
