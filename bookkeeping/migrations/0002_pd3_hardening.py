from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):
    dependencies = [
        ("bookkeeping", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="category",
            name="categories_user_name_type_uniq",
        ),
        migrations.AddConstraint(
            model_name="category",
            constraint=models.UniqueConstraint(
                Lower("name"), "user", "type", name="categories_user_lower_name_type_uniq"
            ),
        ),
        migrations.RemoveConstraint(
            model_name="customer",
            name="customers_user_name_uniq",
        ),
        migrations.AddConstraint(
            model_name="customer",
            constraint=models.UniqueConstraint(
                Lower("name"), "user", name="customers_user_lower_name_uniq"
            ),
        ),
        migrations.RemoveConstraint(
            model_name="supplier",
            name="suppliers_user_name_uniq",
        ),
        migrations.AddConstraint(
            model_name="supplier",
            constraint=models.UniqueConstraint(
                Lower("name"), "user", name="suppliers_user_lower_name_uniq"
            ),
        ),
        migrations.AlterField(
            model_name="category",
            name="user",
            field=models.ForeignKey(
                db_column="user_id", on_delete=django.db.models.deletion.PROTECT,
                related_name="categories", to="accounts.user"
            ),
        ),
        migrations.AlterField(
            model_name="customer",
            name="user",
            field=models.ForeignKey(
                db_column="user_id", on_delete=django.db.models.deletion.PROTECT,
                related_name="customers", to="accounts.user"
            ),
        ),
        migrations.AlterField(
            model_name="supplier",
            name="user",
            field=models.ForeignKey(
                db_column="user_id", on_delete=django.db.models.deletion.PROTECT,
                related_name="suppliers", to="accounts.user"
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="user",
            field=models.ForeignKey(
                db_column="user_id", on_delete=django.db.models.deletion.PROTECT,
                related_name="transactions", to="accounts.user"
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="category",
            field=models.ForeignKey(
                db_column="category_id", on_delete=django.db.models.deletion.PROTECT,
                related_name="transactions", to="bookkeeping.category"
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="customer",
            field=models.ForeignKey(
                blank=True, db_column="customer_id", null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transactions", to="bookkeeping.customer"
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="supplier",
            field=models.ForeignKey(
                blank=True, db_column="supplier_id", null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transactions", to="bookkeeping.supplier"
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="amount",
            field=models.DecimalField(
                decimal_places=2, max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
            ),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["user", "transaction_date"], name="txn_user_date_idx"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(
                fields=["user", "type", "transaction_date"], name="txn_user_type_date_idx"
            ),
        ),
    ]
