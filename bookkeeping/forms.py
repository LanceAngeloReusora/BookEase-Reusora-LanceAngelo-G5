from django import forms
from django.utils import timezone

from .models import Category, Customer, Supplier, Transaction


class StyledFormMixin:
    def style_fields(self):
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} form-control".strip()


class CategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "type"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "e.g. Sales, Rent, Supplies"})}

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.instance.user = user
        self.fields["type"].choices = Category.Type.choices
        self.style_fields()

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        kind = self.cleaned_data.get("type") or self.data.get("type")
        duplicate = Category.objects.filter(user=self.user, name__iexact=name, type=kind)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError("You already have a category with this name and type.")
        return name

    def clean_type(self):
        kind = self.cleaned_data["type"]
        if self.instance.pk and self.instance.type != kind and self.instance.transactions.exists():
            raise forms.ValidationError("A category used by a transaction cannot change its type.")
        return kind

    def save(self, commit=True):
        category = super().save(commit=False)
        category.user = self.user
        if commit:
            category.save()
        return category


class TransactionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            "type",
            "amount",
            "transaction_date",
            "category",
            "description",
            "customer",
            "supplier",
        ]
        widgets = {
            "amount": forms.NumberInput(attrs={"min": "0.01", "step": "0.01", "placeholder": "0.00"}),
            "transaction_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.TextInput(attrs={"maxlength": "255", "placeholder": "Optional note"}),
        }
        labels = {
            "type": "Transaction type",
            "transaction_date": "Transaction date",
            "customer": "Customer (optional, income only)",
            "supplier": "Supplier (optional, expenses only)",
        }

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.instance.user = user
        self.fields["category"].queryset = Category.objects.filter(user=user).order_by("type", "name")
        self.fields["category"].empty_label = "Choose a category"
        self.fields["category"].label_from_instance = lambda category: (
            f"{category.name} · {category.get_type_display()}"
        )
        self.fields["customer"].queryset = Customer.objects.filter(user=user).order_by("name")
        self.fields["supplier"].queryset = Supplier.objects.filter(user=user).order_by("name")
        self.fields["customer"].required = False
        self.fields["supplier"].required = False
        self.fields["customer"].empty_label = "No customer"
        self.fields["supplier"].empty_label = "No supplier"
        self.fields["transaction_date"].widget.attrs["max"] = timezone.localdate().isoformat()
        if not self.instance.pk and not self.initial.get("transaction_date"):
            self.initial["transaction_date"] = timezone.localdate()
        self.style_fields()

    def clean_description(self):
        return (self.cleaned_data.get("description") or "").strip() or None

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("type")
        category = cleaned.get("category")
        date = cleaned.get("transaction_date")
        customer = cleaned.get("customer")
        supplier = cleaned.get("supplier")

        if date and date > timezone.localdate():
            self.add_error("transaction_date", "The transaction date cannot be in the future.")

        if category:
            if category.user_id != self.user.pk:
                self.add_error("category", "Choose a category that belongs to your account.")
            if kind and category.type != kind:
                self.add_error("category", "Choose a category with the same type as this transaction.")

        if kind == Transaction.Type.INCOME:
            if supplier:
                self.add_error("supplier", "Income transactions can only be linked to a customer.")
        elif kind == Transaction.Type.EXPENSE:
            if customer:
                self.add_error("customer", "Expense transactions can only be linked to a supplier.")

        if customer and customer.user_id != self.user.pk:
            self.add_error("customer", "Choose a customer that belongs to your account.")
        if supplier and supplier.user_id != self.user.pk:
            self.add_error("supplier", "Choose a supplier that belongs to your account.")
        return cleaned

    def save(self, commit=True):
        transaction = super().save(commit=False)
        transaction.user = self.user
        if commit:
            transaction.save()
        return transaction


class ContactFormBase(StyledFormMixin, forms.ModelForm):
    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.instance.user = user
        for name in ("email", "phone", "address"):
            self.fields[name].required = False
        self.style_fields()

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        duplicate = self._meta.model.objects.filter(user=self.user, name__iexact=name)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError("A contact with this name already exists in your account.")
        return name

    def save(self, commit=True):
        contact = super().save(commit=False)
        contact.user = self.user
        if commit:
            contact.save()
        return contact


class CustomerForm(ContactFormBase):
    class Meta:
        model = Customer
        fields = ["name", "email", "phone", "address"]
        widgets = {"address": forms.TextInput(attrs={"placeholder": "Street, city, or area"})}


class SupplierForm(ContactFormBase):
    class Meta:
        model = Supplier
        fields = ["name", "email", "phone", "address"]
        widgets = {"address": forms.TextInput(attrs={"placeholder": "Street, city, or area"})}
