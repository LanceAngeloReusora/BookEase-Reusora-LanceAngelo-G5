from datetime import timedelta
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import ActivityLog, User
from .models import Category, Customer, Supplier, Transaction

PASSWORD = "Str0ng-Pass-123"


def make_owner(email="owner@example.com"):
    return User.objects.create_user(email=email, password=PASSWORD, full_name="Olive Owner")


def make_admin(email="admin@example.com"):
    return User.objects.create_superuser(email=email, password=PASSWORD, full_name="Adam Admin")


class TransactionWorkflowTests(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.other_owner = make_owner("other@example.com")
        self.income_category = Category.objects.create(user=self.owner, name="Sales", type="INCOME")
        self.expense_category = Category.objects.create(user=self.owner, name="Supplies", type="EXPENSE")
        self.other_category = Category.objects.create(user=self.other_owner, name="Other Sales", type="INCOME")
        self.client.force_login(self.owner)

    def transaction_data(self, **overrides):
        data = {
            "type": "INCOME",
            "amount": "1250.50",
            "transaction_date": timezone.localdate().isoformat(),
            "category": str(self.income_category.pk),
            "description": "Daily sales",
            "customer": "",
            "supplier": "",
        }
        data.update(overrides)
        return data

    def test_owner_can_view_transaction_page(self):
        response = self.client.get(reverse("bookkeeping:transaction_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Transactions")

    def test_create_transaction_persists_for_logged_in_owner(self):
        response = self.client.post(
            reverse("bookkeeping:transaction_create"), self.transaction_data(), follow=True
        )
        self.assertRedirects(response, reverse("bookkeeping:transaction_list"))
        transaction = Transaction.objects.get(description="Daily sales")
        self.assertEqual(transaction.user, self.owner)
        self.assertEqual(transaction.category, self.income_category)
        self.assertEqual(transaction.amount, Decimal("1250.50"))
        self.assertTrue(
            ActivityLog.objects.filter(
                user=self.owner, action=ActivityLog.Action.CREATE,
                entity_name="transactions", entity_id=transaction.pk,
            ).exists()
        )

    def test_update_transaction(self):
        item = Transaction.objects.create(
            user=self.owner,
            category=self.income_category,
            type=Transaction.Type.INCOME,
            amount=Decimal("100.00"),
            transaction_date=timezone.localdate(),
            description="Old note",
        )
        response = self.client.post(
            reverse("bookkeeping:transaction_update", args=[item.pk]),
            self.transaction_data(amount="450.00", description="Updated note"),
            follow=True,
        )
        self.assertRedirects(response, reverse("bookkeeping:transaction_list"))
        item.refresh_from_db()
        self.assertEqual(item.amount, Decimal("450.00"))
        self.assertEqual(item.description, "Updated note")
        self.assertTrue(self.owner.activity_logs.filter(action="UPDATE", entity_id=item.pk).exists())

    def test_delete_transaction(self):
        item = Transaction.objects.create(
            user=self.owner,
            category=self.expense_category,
            type=Transaction.Type.EXPENSE,
            amount=Decimal("99.00"),
            transaction_date=timezone.localdate(),
        )
        response = self.client.post(reverse("bookkeeping:transaction_delete", args=[item.pk]), follow=True)
        self.assertRedirects(response, reverse("bookkeeping:transaction_list"))
        self.assertFalse(Transaction.objects.filter(pk=item.pk).exists())
        self.assertTrue(self.owner.activity_logs.filter(action="DELETE", entity_id=item.pk).exists())

    def test_other_owner_cannot_view_update_or_delete_transaction(self):
        item = Transaction.objects.create(
            user=self.other_owner,
            category=self.other_category,
            type=Transaction.Type.INCOME,
            amount=Decimal("10.00"),
            transaction_date=timezone.localdate(),
        )
        self.assertEqual(self.client.get(reverse("bookkeeping:transaction_update", args=[item.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("bookkeeping:transaction_update", args=[item.pk]), {}).status_code, 404)
        self.assertEqual(self.client.post(reverse("bookkeeping:transaction_delete", args=[item.pk])).status_code, 404)
        self.assertTrue(Transaction.objects.filter(pk=item.pk).exists())

    def test_category_must_belong_to_owner(self):
        response = self.client.post(
            reverse("bookkeeping:transaction_create"),
            self.transaction_data(category=str(self.other_category.pk)),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(user=self.owner).exists())

    def test_category_type_must_match_transaction_type(self):
        response = self.client.post(
            reverse("bookkeeping:transaction_create"),
            self.transaction_data(type="EXPENSE", category=str(self.income_category.pk)),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(user=self.owner).exists())

    def test_future_date_is_rejected(self):
        future = (timezone.localdate() + timedelta(days=1)).isoformat()
        response = self.client.post(
            reverse("bookkeeping:transaction_create"), self.transaction_data(transaction_date=future)
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(user=self.owner).exists())

    def test_non_positive_amount_is_rejected(self):
        response = self.client.post(
            reverse("bookkeeping:transaction_create"), self.transaction_data(amount="0")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(user=self.owner).exists())

    def test_category_in_use_cannot_be_deleted(self):
        Transaction.objects.create(
            user=self.owner,
            category=self.income_category,
            type=Transaction.Type.INCOME,
            amount=Decimal("15.00"),
            transaction_date=timezone.localdate(),
        )
        response = self.client.post(
            reverse("bookkeeping:category_delete", args=[self.income_category.pk]), follow=True
        )
        self.assertContains(response, "cannot be deleted")
        self.assertTrue(Category.objects.filter(pk=self.income_category.pk).exists())

    def test_customer_and_supplier_links(self):
        customer = Customer.objects.create(user=self.owner, name="Walk-in Customer")
        supplier = Supplier.objects.create(user=self.owner, name="Paper Depot")
        income_response = self.client.post(
            reverse("bookkeeping:transaction_create"),
            self.transaction_data(customer=str(customer.pk)),
        )
        expense_response = self.client.post(
            reverse("bookkeeping:transaction_create"),
            self.transaction_data(
                type="EXPENSE", category=str(self.expense_category.pk), supplier=str(supplier.pk),
                amount="200.00", description="Paper stock",
            ),
        )
        self.assertEqual(income_response.status_code, 302)
        self.assertEqual(expense_response.status_code, 302)
        self.assertTrue(Transaction.objects.filter(customer=customer, type="INCOME").exists())
        self.assertTrue(Transaction.objects.filter(supplier=supplier, type="EXPENSE").exists())

    def test_filters_search_by_description(self):
        Transaction.objects.create(
            user=self.owner,
            category=self.income_category,
            type=Transaction.Type.INCOME,
            amount=Decimal("120.00"),
            transaction_date=timezone.localdate(),
            description="Online orders",
        )
        response = self.client.get(reverse("bookkeeping:transaction_list"), {"q": "online"})
        self.assertContains(response, "Online orders")
        self.assertNotContains(response, "Daily sales")

    def test_dashboard_uses_saved_transactions_for_totals(self):
        Transaction.objects.create(
            user=self.owner, category=self.income_category, type="INCOME",
            amount=Decimal("1000.00"), transaction_date=timezone.localdate(),
        )
        Transaction.objects.create(
            user=self.owner, category=self.expense_category, type="EXPENSE",
            amount=Decimal("250.00"), transaction_date=timezone.localdate(),
        )
        response = self.client.get(reverse("accounts:owner_dashboard"))
        self.assertContains(response, "₱1000.00")
        self.assertContains(response, "₱250.00")
        self.assertContains(response, "₱750.00")

    def test_delete_endpoint_rejects_get(self):
        item = Transaction.objects.create(
            user=self.owner, category=self.income_category, type="INCOME",
            amount=Decimal("20.00"), transaction_date=timezone.localdate(),
        )
        response = self.client.get(reverse("bookkeeping:transaction_delete", args=[item.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Transaction.objects.filter(pk=item.pk).exists())

    def test_missing_transaction_id_returns_404(self):
        response = self.client.get(reverse("bookkeeping:transaction_update", args=[999999]))
        self.assertEqual(response.status_code, 404)

    def test_invalid_contact_kind_returns_404(self):
        response = self.client.get(reverse("bookkeeping:contact_list", kwargs={"kind": "staff"}))
        self.assertEqual(response.status_code, 404)

    def test_csrf_is_required_for_transaction_create(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.owner)
        response = csrf_client.post(
            reverse("bookkeeping:transaction_create"), self.transaction_data()
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Transaction.objects.filter(user=self.owner).exists())

    def test_transaction_list_is_scoped_to_current_owner(self):
        Transaction.objects.create(
            user=self.other_owner, category=self.other_category, type="INCOME",
            amount=Decimal("55.00"), transaction_date=timezone.localdate(),
            description="Private other-owner entry",
        )
        Transaction.objects.create(
            user=self.owner, category=self.income_category, type="INCOME",
            amount=Decimal("12.00"), transaction_date=timezone.localdate(),
            description="My own entry",
        )
        response = self.client.get(reverse("bookkeeping:transaction_list"))
        self.assertContains(response, "My own entry")
        self.assertNotContains(response, "Private other-owner entry")

    def test_duplicate_category_name_case_insensitive_is_rejected(self):
        response = self.client.post(
            reverse("bookkeeping:category_create"), {"name": "sales", "type": "INCOME"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.context["form"].errors)
        self.assertEqual(Category.objects.filter(user=self.owner, type="INCOME").count(), 1)

    def test_duplicate_contact_name_case_insensitive_is_rejected(self):
        Customer.objects.create(user=self.owner, name="Walk-in Customer")
        response = self.client.post(
            reverse("bookkeeping:contact_create", kwargs={"kind": "customers"}),
            {"name": "walk-in customer", "email": "", "phone": "", "address": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.context["form"].errors)
        self.assertEqual(Customer.objects.filter(user=self.owner).count(), 1)

    def test_database_prevents_case_insensitive_duplicate_category(self):
        from django.db import IntegrityError, transaction as db_transaction

        with self.assertRaises(IntegrityError), db_transaction.atomic():
            Category.objects.create(user=self.owner, name="sales", type="INCOME")

    def test_transaction_delete_requires_confirmation_in_ui(self):
        Transaction.objects.create(
            user=self.owner, category=self.income_category, type="INCOME",
            amount=Decimal("20.00"), transaction_date=timezone.localdate(),
        )
        response = self.client.get(reverse("bookkeeping:transaction_list"))
        self.assertContains(response, "confirm('Delete this transaction?')")

    def test_owner_cannot_update_another_owners_category_or_contact(self):
        foreign_customer = Customer.objects.create(user=self.other_owner, name="Other Customer")
        self.assertEqual(
            self.client.get(reverse("bookkeeping:category_update", args=[self.other_category.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("bookkeeping:contact_update", kwargs={"kind": "customers", "pk": foreign_customer.pk})).status_code,
            404,
        )

    def test_invalid_transaction_form_does_not_persist(self):
        invalid = self.transaction_data(amount="not-a-number")
        response = self.client.post(reverse("bookkeeping:transaction_create"), invalid)
        self.assertEqual(response.status_code, 200)
        self.assertIn("amount", response.context["form"].errors)
        self.assertFalse(Transaction.objects.filter(user=self.owner).exists())


class BookkeepingAccessTests(TestCase):
    def test_logged_out_user_is_redirected_to_login(self):
        url = reverse("bookkeeping:transaction_list")
        response = self.client.get(url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}", fetch_redirect_response=False)

    def test_admin_cannot_access_owner_bookkeeping_pages(self):
        self.client.force_login(make_admin())
        for name in (
            "bookkeeping:transaction_list",
            "bookkeeping:category_list",
            "bookkeeping:contact_list",
        ):
            kwargs = {"kind": "customers"} if name.endswith("contact_list") else None
            response = self.client.get(reverse(name, kwargs=kwargs))
            with self.subTest(page=name):
                self.assertEqual(response.status_code, 403)


class SupportingRecordsTests(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.client.force_login(self.owner)

    def test_category_create_and_list(self):
        response = self.client.post(
            reverse("bookkeeping:category_create"),
            {"name": "Consulting", "type": "INCOME"},
            follow=True,
        )
        self.assertRedirects(response, reverse("bookkeeping:category_list"))
        self.assertTrue(Category.objects.filter(user=self.owner, name="Consulting", type="INCOME").exists())
        self.assertContains(response, "Consulting")

    def test_duplicate_category_name_and_type_is_rejected(self):
        Category.objects.create(user=self.owner, name="Sales", type="INCOME")
        response = self.client.post(
            reverse("bookkeeping:category_create"),
            {"name": "sales", "type": "INCOME"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Category.objects.filter(user=self.owner).count(), 1)

    def test_customer_create_and_contact_page(self):
        response = self.client.post(
            reverse("bookkeeping:contact_create", args=["customers"]),
            {"name": "First Customer", "email": "first@example.com", "phone": "09171234567", "address": "Cebu"},
            follow=True,
        )
        self.assertRedirects(response, reverse("bookkeeping:contact_list", args=["customers"]))
        self.assertTrue(Customer.objects.filter(user=self.owner, name="First Customer").exists())
        self.assertContains(response, "First Customer")

    def test_supplier_create_page_loads_and_persists(self):
        response = self.client.post(
            reverse("bookkeeping:contact_create", args=["suppliers"]),
            {"name": "Office Depot", "email": "", "phone": "", "address": ""},
            follow=True,
        )
        self.assertRedirects(response, reverse("bookkeeping:contact_list", args=["suppliers"]))
        self.assertTrue(Supplier.objects.filter(user=self.owner, name="Office Depot").exists())
