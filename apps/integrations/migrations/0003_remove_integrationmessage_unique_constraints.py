from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0002_alter_integrationmessage_uniq_idempotency"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="integrationmessage",
            name="uniq_integration_message_reference",
        ),
        migrations.RemoveConstraint(
            model_name="integrationmessage",
            name="uniq_integration_idempotency",
        ),
    ]
