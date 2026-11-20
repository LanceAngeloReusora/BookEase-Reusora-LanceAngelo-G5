# Generated for the BookEase bookkeeping vertical slice.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def add_transaction_category_type_fk(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            'ALTER TABLE "transactions" '
            'ADD CONSTRAINT "transactions_category_type_fk" '
            'FOREIGN KEY ("category_id", "type") '
            'REFERENCES "categories" ("category_id", "type") ON DELETE RESTRICT'
        )


def remove_transaction_category_type_fk(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            'ALTER TABLE "transactions" DROP CONSTRAINT "transactions_category_type_fk"'
        )


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("category_id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=50)),
                ("type", models.CharField(choices=[("INCOME", "Income"), ("EXPENSE", "Expense")], max_length=7)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(db_column="user_id", on_delete=django.db.models.deletion.RESTRICT, related_name="categories", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "categories", "ordering": ["type", "name"]},
        ),
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("customer_id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("email", models.EmailField(blank=True, max_length=100, null=True)),
                ("phone", models.CharField(blank=True, max_length=20, null=True)),
                ("address", models.CharField(blank=True, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(db_column="user_id", on_delete=django.db.models.deletion.RESTRICT, related_name="customers", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "customers", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Supplier",
            fields=[
                ("supplier_id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("email", models.EmailField(blank=True, max_length=100, null=True)),
                ("phone", models.CharField(blank=True, max_length=20, null=True)),
                ("address", models.CharField(blank=True, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(db_column="user_id", on_delete=django.db.models.deletion.RESTRICT, related_name="suppliers", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "suppliers", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Transaction",
            fields=[
                ("transaction_id", models.AutoField(primary_key=True, serialize=False)),
                ("type", models.CharField(choices=[("INCOME", "Income"), ("EXPENSE", "Expense")], max_length=7)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("transaction_date", models.DateField()),
                ("description", models.CharField(blank=True, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(db_column="category_id", on_delete=django.db.models.deletion.RESTRICT, related_name="transactions", to="bookkeeping.category")),
                ("customer", models.ForeignKey(blank=True, db_column="customer_id", null=True, on_delete=django.db.models.deletion.RESTRICT, related_name="transactions", to="bookkeeping.customer")),
                ("supplier", models.ForeignKey(blank=True, db_column="supplier_id", null=True, on_delete=django.db.models.deletion.RESTRICT, related_name="transactions", to="bookkeeping.supplier")),
                ("user", models.ForeignKey(db_column="user_id", on_delete=django.db.models.deletion.RESTRICT, related_name="transactions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "transactions", "ordering": ["-transaction_date", "-transaction_id"]},
        ),
        migrations.AddConstraint(
            model_name="category",
            constraint=models.CheckConstraint(condition=models.Q(("type__in", ["INCOME", "EXPENSE"])), name="categories_type_check"),
        ),
        migrations.AddConstraint(
            model_name="category",
            constraint=models.UniqueConstraint(fields=("user", "name", "type"), name="categories_user_name_type_uniq"),
        ),
        migrations.AddConstraint(
            model_name="category",
            constraint=models.UniqueConstraint(fields=("category_id", "type"), name="categories_id_type_uniq"),
        ),
        migrations.AddConstraint(
            model_name="customer",
            constraint=models.UniqueConstraint(fields=("user", "name"), name="customers_user_name_uniq"),
        ),
        migrations.AddConstraint(
            model_name="supplier",
            constraint=models.UniqueConstraint(fields=("user", "name"), name="suppliers_user_name_uniq"),
        ),
        migrations.AddConstraint(
            model_name="transaction",
            constraint=models.CheckConstraint(condition=models.Q(("type__in", ["INCOME", "EXPENSE"])), name="transactions_type_check"),
        ),
        migrations.AddConstraint(
            model_name="transaction",
            constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="transactions_amount_positive"),
        ),
        migrations.AddConstraint(
            model_name="transaction",
            constraint=models.CheckConstraint(
                condition=(models.Q(("supplier__isnull", True), ("type", "INCOME")) | models.Q(("customer__isnull", True), ("type", "EXPENSE"))),
                name="transactions_contact_matches_type",
            ),
        ),
        # BR-14: the transaction type must match the referenced category type.
        migrations.RunPython(add_transaction_category_type_fk, remove_transaction_category_type_fk),
    ]
