from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction as db_transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from bookkeeping.models import Transaction

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

@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    user = form.save()
                    log_activity(
                        user, ActivityLog.Action.REGISTER, "users", user.pk, "Registered a new account"
                    )
            except IntegrityError:
                form.add_error("email", "An account with this email already exists.")
            else:
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
@require_GET
def dashboard(request):
    """Send each user to the dashboard that matches their role."""
    if request.user.is_admin:
        return redirect("accounts:admin_dashboard")
    return redirect("accounts:owner_dashboard")


@owner_required
@require_GET
def owner_dashboard(request):
    """Owner dashboard totals are calculated from the owner's saved transactions."""
    transactions = Transaction.objects.filter(user=request.user)
    date_from_raw = request.GET.get("date_from", "").strip()
    date_to_raw = request.GET.get("date_to", "").strip()
    date_from = parse_date(date_from_raw) if date_from_raw else None
    date_to = parse_date(date_to_raw) if date_to_raw else None

    if date_from_raw and date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    elif date_from_raw:
        messages.error(request, "Enter a valid dashboard start date.")
    if date_to_raw and date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    elif date_to_raw:
        messages.error(request, "Enter a valid dashboard end date.")
    if date_from and date_to and date_to < date_from:
        messages.error(request, "The dashboard end date cannot be earlier than the start date.")
        transactions = Transaction.objects.filter(user=request.user).none()

    income_total = transactions.filter(type=Transaction.Type.INCOME).aggregate(total=Sum("amount"))["total"] or 0
    expense_total = transactions.filter(type=Transaction.Type.EXPENSE).aggregate(total=Sum("amount"))["total"] or 0
    recent_transactions = Transaction.objects.filter(user=request.user).select_related("category", "customer", "supplier")[:5]
    recent = ActivityLog.objects.filter(user=request.user)[:8]
    return render(
        request,
        "accounts/dashboard_owner.html",
        {
            "recent_activity": recent,
            "income_total": income_total,
            "expense_total": expense_total,
            "net_income": income_total - expense_total,
            "recent_transactions": recent_transactions,
            "date_from": date_from_raw,
            "date_to": date_to_raw,
        },
    )


@admin_required
@require_GET
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
@require_GET
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

    with db_transaction.atomic():
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
@require_GET
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
@require_GET
def profile(request):
    return render(request, "accounts/profile.html", {"profile_user": request.user})


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    form.save()
                    log_activity(
                        request.user, ActivityLog.Action.UPDATE, "users", request.user.pk, "Updated profile"
                    )
            except IntegrityError:
                form.add_error("email", "Another account already uses this email.")
            else:
                messages.success(request, "Your profile was updated successfully.")
                return redirect("accounts:profile")
        messages.error(request, "Could not update your profile. Please fix the errors below.")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def password_change(request):
    if request.method == "POST":
        form = StyledPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                user = form.save()
                log_activity(user, ActivityLog.Action.UPDATE, "users", user.pk, "Changed password")
            update_session_auth_hash(request, user)  # keep the user logged in
            messages.success(request, "Your password was changed successfully.")
            return redirect("accounts:profile")
        messages.error(request, "Could not change your password. Please fix the errors below.")
    else:
        form = StyledPasswordChangeForm(request.user)
    return render(request, "accounts/password_change.html", {"form": form})
