from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="accounts:dashboard", permanent=False)),
    path("", include("accounts.urls")),
    path("django-admin/", admin.site.urls),
]
