from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0004_fulfillment_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="fulfillmentorder",
            name="return_delivery_note_name",
            field=models.CharField(blank=True, max_length=140),
        ),
        migrations.AddField(
            model_name="fulfillmentorder",
            name="return_delivery_note_submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="fulfillmentorder",
            name="return_payload",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
