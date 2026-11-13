from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import ActivityLog
from .utils import log_activity


@receiver(user_logged_in)
def record_login(sender, request, user, **kwargs):
    log_activity(user, ActivityLog.Action.LOGIN, "users", user.pk, "Logged in")


@receiver(user_logged_out)
def record_logout(sender, request, user, **kwargs):
    log_activity(user, ActivityLog.Action.LOGOUT, "users", getattr(user, "pk", None), "Logged out")
