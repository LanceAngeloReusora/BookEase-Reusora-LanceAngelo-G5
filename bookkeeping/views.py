from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction as db_transaction
from django.db.models import Count
from django.db.models import Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.decorators import owner_required
from accounts.models import ActivityLog
from accounts.utils import log_activity

from .forms import CategoryForm, CustomerForm, SupplierForm, TransactionForm
from .models import Category, Customer, Supplier, Transaction


@owner_required
@require_GET
def transaction_list(request):
    query = request.GET.get("q", "").strip()
    kind = request.GET.get("type", "").strip().upper()
    category_id = request.GET.get("category", "").strip()
    date_from_raw = request.GET.get("date_from", "").strip()
    date_to_raw = request.GET.get("date_to", "").strip()
    date_from = parse_date(date_from_raw) if date_from_raw else None
    date_to = parse_date(date_to_raw) if date_to_raw else None

    transactions = Transaction.objects.filter(user=request.user).select_related(
        "category", "customer", "supplier"
    )
    if query:
        transactions = transactions.filter(
            Q(description__icontains=query)
            | Q(category__name__icontains=query)
            | Q(customer__name__icontains=query)
            | Q(supplier__name__icontains=query)
        )
    if kind in Transaction.Type.values:
        transactions = transactions.filter(type=kind)
    else:
        kind = ""
    if category_id.isdigit():
        transactions = transactions.filter(category_id=category_id, category__user=request.user)
    else:
        category_id = ""
    if date_from_raw and date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    elif date_from_raw:
        messages.error(request, "Enter a valid start date.")
    if date_to_raw and date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    elif date_to_raw:
        messages.error(request, "Enter a valid end date.")
    if date_from and date_to and date_to < date_from:
        messages.error(request, "The end date cannot be earlier than the start date.")
        transactions = Transaction.objects.filter(user=request.user).none()

    income_total = transactions.filter(type=Transaction.Type.INCOME).aggregate(total=Sum("amount"))["total"] or 0
    expense_total = transactions.filter(type=Transaction.Type.EXPENSE).aggregate(total=Sum("amount"))["total"] or 0
    page = Paginator(transactions, 10).get_page(request.GET.get("page"))
    return render(
        request,
        "bookkeeping/transaction_list.html",
        {
            "page": page,
            "query": query,
            "type_filter": kind,
            "category_filter": category_id,
            "date_from": date_from_raw,
            "date_to": date_to_raw,
            "categories": Category.objects.filter(user=request.user),
            "income_total": income_total,
            "expense_total": expense_total,
        },
    )


@owner_required
@require_http_methods(["GET", "POST"])
def transaction_create(request):
    form = TransactionForm(request.POST if request.method == "POST" else None, user=request.user)
    if request.method == "POST":
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    item = form.save()
                    log_activity(
                        request.user,
                        ActivityLog.Action.CREATE,
                        "transactions",
                        item.pk,
                        f"Recorded {item.get_type_display().lower()} of PHP {item.amount}",
                    )
            except IntegrityError:
                form.add_error(None, "The transaction conflicts with a database rule. Review the values and try again.")
            else:
                messages.success(request, "Transaction recorded successfully.")
                return redirect("bookkeeping:transaction_list")
        messages.error(request, "Transaction was not saved. Please review the errors below.")
    return render(
        request,
        "bookkeeping/transaction_form.html",
        {"form": form, "heading": "Add transaction", "submit_label": "Save transaction"},
    )


@owner_required
@require_http_methods(["GET", "POST"])
def transaction_update(request, pk):
    item = get_object_or_404(Transaction, pk=pk, user=request.user)
    form = TransactionForm(request.POST if request.method == "POST" else None, instance=item, user=request.user)
    if request.method == "POST":
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    item = form.save()
                    log_activity(
                        request.user,
                        ActivityLog.Action.UPDATE,
                        "transactions",
                        item.pk,
                        f"Updated transaction #{item.pk}",
                    )
            except IntegrityError:
                form.add_error(None, "The transaction conflicts with a database rule. Review the values and try again.")
            else:
                messages.success(request, "Transaction updated successfully.")
                return redirect("bookkeeping:transaction_list")
        messages.error(request, "Transaction was not updated. Please review the errors below.")
    return render(
        request,
        "bookkeeping/transaction_form.html",
        {"form": form, "heading": "Edit transaction", "submit_label": "Save changes", "item": item},
    )


@owner_required
@require_POST
def transaction_delete(request, pk):
    item = get_object_or_404(Transaction, pk=pk, user=request.user)
    item_id = item.pk
    with db_transaction.atomic():
        item.delete()
        log_activity(
            request.user, ActivityLog.Action.DELETE, "transactions", item_id,
            f"Deleted transaction #{item_id}"
        )
    messages.success(request, "Transaction deleted successfully.")
    return redirect("bookkeeping:transaction_list")


@owner_required
@require_GET
def category_list(request):
    categories = Category.objects.filter(user=request.user).annotate(
        transaction_count=Count("transactions")
    )
    return render(request, "bookkeeping/category_list.html", {"categories": categories})


@owner_required
@require_http_methods(["GET", "POST"])
def category_create(request):
    form = CategoryForm(request.POST if request.method == "POST" else None, user=request.user)
    if request.method == "POST":
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    item = form.save()
                    log_activity(request.user, ActivityLog.Action.CREATE, "categories", item.pk, f"Created category {item.name}")
            except IntegrityError:
                form.add_error(None, "A category with these details already exists. Refresh and try again.")
            else:
                messages.success(request, "Category created successfully.")
                return redirect("bookkeeping:category_list")
        messages.error(request, "Category was not saved. Please review the errors below.")
    return render(request, "bookkeeping/category_form.html", {"form": form, "heading": "Add category"})


@owner_required
@require_http_methods(["GET", "POST"])
def category_update(request, pk):
    item = get_object_or_404(Category, pk=pk, user=request.user)
    form = CategoryForm(request.POST if request.method == "POST" else None, instance=item, user=request.user)
    if request.method == "POST":
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    item = form.save()
                    log_activity(request.user, ActivityLog.Action.UPDATE, "categories", item.pk, f"Updated category {item.name}")
            except IntegrityError:
                form.add_error(None, "A category with these details already exists. Refresh and try again.")
            else:
                messages.success(request, "Category updated successfully.")
                return redirect("bookkeeping:category_list")
        messages.error(request, "Category was not updated. Please review the errors below.")
    return render(request, "bookkeeping/category_form.html", {"form": form, "heading": "Edit category"})


@owner_required
@require_POST
def category_delete(request, pk):
    item = get_object_or_404(Category, pk=pk, user=request.user)
    try:
        with db_transaction.atomic():
            item.delete()
            log_activity(request.user, ActivityLog.Action.DELETE, "categories", pk, f"Deleted category {item.name}")
    except ProtectedError:
        messages.error(request, "This category is used by a transaction and cannot be deleted.")
    else:
        messages.success(request, "Category deleted successfully.")
    return redirect("bookkeeping:category_list")


def _contact_config(kind):
    config = {
        "customers": (Customer, CustomerForm, "Customer", "customer_id"),
        "suppliers": (Supplier, SupplierForm, "Supplier", "supplier_id"),
    }
    try:
        return config[kind]
    except KeyError:
        raise Http404("Contact type not found.")


@owner_required
@require_GET
def contact_list(request, kind):
    model, form_class, label, id_field = _contact_config(kind)
    contacts = model.objects.filter(user=request.user)
    return render(
        request,
        "bookkeeping/contact_list.html",
        {"contacts": contacts, "kind": kind, "contact_label": label, "heading": f"{label}s"},
    )


@owner_required
@require_http_methods(["GET", "POST"])
def contact_create(request, kind):
    model, form_class, label, id_field = _contact_config(kind)
    form = form_class(request.POST if request.method == "POST" else None, user=request.user)
    if request.method == "POST":
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    contact = form.save()
                    log_activity(request.user, ActivityLog.Action.CREATE, kind, contact.pk, f"Created {label.lower()} {contact.name}")
            except IntegrityError:
                form.add_error(None, f"A {label.lower()} with this name already exists. Refresh and try again.")
            else:
                messages.success(request, f"{label} created successfully.")
                return redirect("bookkeeping:contact_list", kind=kind)
        messages.error(request, f"{label} was not saved. Please review the errors below.")
    return render(request, "bookkeeping/contact_form.html", {"form": form, "heading": f"Add {label.lower()}", "kind": kind})


@owner_required
@require_http_methods(["GET", "POST"])
def contact_update(request, kind, pk):
    model, form_class, label, id_field = _contact_config(kind)
    contact = get_object_or_404(model, pk=pk, user=request.user)
    form = form_class(request.POST if request.method == "POST" else None, instance=contact, user=request.user)
    if request.method == "POST":
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    contact = form.save()
                    log_activity(request.user, ActivityLog.Action.UPDATE, kind, contact.pk, f"Updated {label.lower()} {contact.name}")
            except IntegrityError:
                form.add_error(None, f"A {label.lower()} with this name already exists. Refresh and try again.")
            else:
                messages.success(request, f"{label} updated successfully.")
                return redirect("bookkeeping:contact_list", kind=kind)
        messages.error(request, f"{label} was not updated. Please review the errors below.")
    return render(request, "bookkeeping/contact_form.html", {"form": form, "heading": f"Edit {label.lower()}", "kind": kind})


@owner_required
@require_POST
def contact_delete(request, kind, pk):
    model, form_class, label, id_field = _contact_config(kind)
    contact = get_object_or_404(model, pk=pk, user=request.user)
    try:
        with db_transaction.atomic():
            contact.delete()
            log_activity(request.user, ActivityLog.Action.DELETE, kind, pk, f"Deleted {label.lower()} {contact.name}")
    except ProtectedError:
        messages.error(request, f"This {label.lower()} is linked to a transaction and cannot be deleted.")
    else:
        messages.success(request, f"{label} deleted successfully.")
    return redirect("bookkeeping:contact_list", kind=kind)
