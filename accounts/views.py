from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .decorators import admin_required, owner_required
from .forms import (
    EmailAuthenticationForm,
    ProfileForm,
    RegistrationForm,
    StyledPasswordChangeForm,
)
from .models import ActivityLog, User
from .utils import log_activity


# --- Registration / login / logout ------------------------------------------

def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_activity(
                user, ActivityLog.Action.REGISTER, "users", user.pk, "Registered a new account"
            )
            messages.success(request, "Account created successfully. You can now log in.")
            return redirect("accounts:login")
        messages.error(request, "Registration failed. Please fix the errors below.")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


class BookEaseLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Welcome back, {form.get_user().get_short_name()}!")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Login failed. Please check your details.")
        return super().form_invalid(form)


@require_POST
def logout_view(request):
    logout(request)  # ends the session; the user_logged_out signal writes the log
    messages.success(request, "You have been logged out.")
    return redirect("accounts:login")


# --- Role-based dashboards --------------------------------------------------

@login_required
def dashboard(request):
    """Send each user to the dashboard that matches their role."""
    if request.user.is_admin:
        return redirect("accounts:admin_dashboard")
    return redirect("accounts:owner_dashboard")


@owner_required
def owner_dashboard(request):
    recent = ActivityLog.objects.filter(user=request.user)[:8]
    return render(request, "accounts/dashboard_owner.html", {"recent_activity": recent})


@admin_required
def admin_dashboard(request):
    users = User.objects.all()
    context = {
        "total_users": users.count(),
        "owner_count": users.filter(role=User.Role.OWNER).count(),
        "admin_count": users.filter(role=User.Role.ADMIN).count(),
        "inactive_count": users.filter(is_active=False).count(),
        "recent_users": users.order_by("-created_at")[:5],
        "recent_activity": ActivityLog.objects.select_related("user")[:8],
    }
    return render(request, "accounts/dashboard_admin.html", context)


@admin_required
def admin_users(request):
    query = request.GET.get("q", "").strip()
    users = User.objects.order_by("-created_at")
    if query:
        users = users.filter(
            Q(full_name__icontains=query)
            | Q(email__icontains=query)
            | Q(business_name__icontains=query)
        )
    page = Paginator(users, 10).get_page(request.GET.get("page"))
    return render(request, "accounts/admin_users.html", {"page": page, "query": query})


@admin_required
@require_POST
def admin_user_toggle(request, pk):
    """Deactivate or reactivate an account. Accounts are never deleted (BR-04, BR-05)."""
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("accounts:admin_users")

    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    state = "activated" if target.is_active else "deactivated"
    log_activity(
        request.user, ActivityLog.Action.UPDATE, "users", target.pk, f"Account {state}: {target.email}"
    )
    messages.success(request, f"{target.email} has been {state}.")
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect("accounts:admin_users")


@admin_required
def admin_activity(request):
    logs = ActivityLog.objects.select_related("user")
    action = request.GET.get("action", "").strip().upper()
    if action in ActivityLog.Action.values:
        logs = logs.filter(action=action)
    else:
        action = ""
    page = Paginator(logs, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "accounts/admin_activity.html",
        {"page": page, "action": action, "actions": ActivityLog.Action.choices},
    )


# --- Profile (always the logged-in user's own record) -----------------------

@login_required
def profile(request):
    return render(request, "accounts/profile.html", {"profile_user": request.user})


@login_required
def profile_edit(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            log_activity(
                request.user, ActivityLog.Action.UPDATE, "users", request.user.pk, "Updated profile"
            )
            messages.success(request, "Your profile was updated successfully.")
            return redirect("accounts:profile")
        messages.error(request, "Could not update your profile. Please fix the errors below.")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required
def password_change(request):
    if request.method == "POST":
        form = StyledPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keep the user logged in
            log_activity(user, ActivityLog.Action.UPDATE, "users", user.pk, "Changed password")
            messages.success(request, "Your password was changed successfully.")
            return redirect("accounts:profile")
        messages.error(request, "Could not change your password. Please fix the errors below.")
    else:
        form = StyledPasswordChangeForm(request.user)
    return render(request, "accounts/password_change.html", {"form": form})
