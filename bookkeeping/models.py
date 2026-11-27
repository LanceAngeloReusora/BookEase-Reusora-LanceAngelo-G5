from django.conf import settings
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone


class Category(models.Model):
    """An owner-specific income or expense category (SDD: categories)."""

    class Type(models.TextChoices):
        INCOME = "INCOME", "Income"
        EXPENSE = "EXPENSE", "Expense"

    category_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="categories",
        db_column="user_id",
    )
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=7, choices=Type.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories"
        ordering = ["type", "name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(type__in=["INCOME", "EXPENSE"]),
                name="categories_type_check",
            ),
            models.UniqueConstraint(
                Lower("name"), "user", "type", name="categories_user_lower_name_type_uniq"
            ),
            models.UniqueConstraint(
                fields=["category_id", "type"], name="categories_id_type_uniq"
            ),
        ]

    def clean(self):
        super().clean()
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValidationError({"name": "Enter a category name."})

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Customer(models.Model):
    """A business owner's customer contact (SDD: customers)."""

    customer_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="customers",
        db_column="user_id",
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "customers"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "user", name="customers_user_lower_name_uniq"
            )
        ]

    def clean(self):
        super().clean()
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValidationError({"name": "Enter a customer name."})

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """A business owner's supplier contact (SDD: suppliers)."""

    supplier_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="suppliers",
        db_column="user_id",
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "suppliers"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "user", name="suppliers_user_lower_name_uniq"
            )
        ]

    def clean(self):
        super().clean()
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValidationError({"name": "Enter a supplier name."})

    def __str__(self):
        return self.name


class Transaction(models.Model):
    """An income or expense record (SDD: transactions)."""

    class Type(models.TextChoices):
        INCOME = "INCOME", "Income"
        EXPENSE = "EXPENSE", "Expense"

    transaction_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transactions",
        db_column="user_id",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="transactions",
        db_column="category_id",
    )
    type = models.CharField(max_length=7, choices=Type.choices)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    transaction_date = models.DateField()
    description = models.CharField(max_length=255, blank=True, null=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="transactions",
        db_column="customer_id",
        blank=True,
        null=True,
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="transactions",
        db_column="supplier_id",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transactions"
        ordering = ["-transaction_date", "-transaction_id"]
        indexes = [
            models.Index(fields=["user", "transaction_date"], name="txn_user_date_idx"),
            models.Index(fields=["user", "type", "transaction_date"], name="txn_user_type_date_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(type__in=["INCOME", "EXPENSE"]),
                name="transactions_type_check",
            ),
            models.CheckConstraint(
                condition=Q(amount__gt=0), name="transactions_amount_positive"
            ),
            models.CheckConstraint(
                condition=(
                    Q(type="INCOME", supplier__isnull=True)
                    | Q(type="EXPENSE", customer__isnull=True)
                ),
                name="transactions_contact_matches_type",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "The amount must be greater than zero."
        if self.transaction_date and self.transaction_date > timezone.localdate():
            errors["transaction_date"] = "The transaction date cannot be in the future."

        if self.category_id:
            category = self.category
            if self.user_id and category.user_id != self.user_id:
                errors["category"] = "Choose a category that belongs to your account."
            if self.type and category.type != self.type:
                errors["category"] = "The category type must match the transaction type."

        if self.customer_id:
            if self.type != self.Type.INCOME:
                errors["customer"] = "Only income transactions can be linked to a customer."
            elif self.user_id and self.customer.user_id != self.user_id:
                errors["customer"] = "Choose a customer that belongs to your account."

        if self.supplier_id:
            if self.type != self.Type.EXPENSE:
                errors["supplier"] = "Only expense transactions can be linked to a supplier."
            elif self.user_id and self.supplier.user_id != self.user_id:
                errors["supplier"] = "Choose a supplier that belongs to your account."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.get_type_display()} ₱{self.amount} on {self.transaction_date}"
