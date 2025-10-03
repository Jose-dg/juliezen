from django.db import migrations, models
import django.db.models


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="integrationmessage",
            name="uniq_integration_idempotency",
        ),
        migrations.AddConstraint(
            model_name="integrationmessage",
            constraint=models.UniqueConstraint(
                condition=models.Q(("idempotency_key__gt", "")),
                fields=("organization_id", "integration", "direction", "idempotency_key"),
                name="uniq_integration_idempotency",
            ),
        ),
    ]
