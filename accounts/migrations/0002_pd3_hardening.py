import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activitylog",
            name="user",
            field=models.ForeignKey(
                db_column="user_id",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="activity_logs",
                to="accounts.user",
            ),
        ),
    ]
