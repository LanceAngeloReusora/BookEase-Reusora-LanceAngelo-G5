from django.contrib import admin

from .models import Category, Customer, Supplier, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "user", "created_at")
    list_filter = ("type",)
    search_fields = ("name", "user__email")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "user", "created_at")
    search_fields = ("name", "email", "user__email")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "user", "created_at")
    search_fields = ("name", "email", "user__email")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "transaction_date", "type", "amount", "category", "user")
    list_filter = ("type", "transaction_date")
    search_fields = ("description", "category__name", "user__email")
    readonly_fields = ("created_at", "updated_at")
