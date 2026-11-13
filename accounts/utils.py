from .models import ActivityLog


def log_activity(user, action, entity_name=None, entity_id=None, details=None):
    """Write one activity log entry (BR-22)."""
    if user is None or not getattr(user, "pk", None):
        return None
    return ActivityLog.objects.create(
        user=user,
        action=action,
        entity_name=entity_name,
        entity_id=entity_id,
        details=(details or "")[:255] or None,
    )
