from django.contrib import admin

from .models import ActivityLog, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "business_name", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("email", "full_name", "business_name")
    readonly_fields = ("password", "last_login", "created_at")
    exclude = ("groups", "user_permissions")

    def has_add_permission(self, request):
        return False  # create users through registration or `createsuperuser`

    def has_delete_permission(self, request, obj=None):
        return False  # accounts are deactivated, never deleted (BR-04)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "entity_name", "entity_id", "details")
    list_filter = ("action",)
    search_fields = ("user__email", "details")

    # Log entries cannot be edited or deleted (BR-23).
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
