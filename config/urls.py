from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="accounts:dashboard", permanent=False)),
    path("", include("accounts.urls")),
    path("", include("bookkeeping.urls")),
    path("django-admin/", admin.site.urls),
]


# Custom non-debug error pages. Django uses these handlers when DEBUG=False.
handler403 = "config.error_views.permission_denied"
handler404 = "config.error_views.page_not_found"
handler500 = "config.error_views.server_error"
