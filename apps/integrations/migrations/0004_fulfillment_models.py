import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0003_remove_integrationmessage_unique_constraints"),
    ]

    operations = [
        migrations.CreateModel(
            name="FulfillmentItemMap",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("organization_id", models.UUIDField(db_index=True)),
                (
                    "source",
                    models.CharField(
                        choices=[("erpnext", "ERPNext"), ("shopify", "Shopify")],
                        max_length=32,
                    ),
                ),
                ("source_company", models.CharField(max_length=140)),
                ("source_item_code", models.CharField(max_length=140)),
                ("target_company", models.CharField(max_length=140)),
                ("target_item_code", models.CharField(max_length=140)),
                ("warehouse", models.CharField(blank=True, max_length=140)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("organization_id", "source", "source_company", "source_item_code"),
            },
        ),
        migrations.CreateModel(
            name="FulfillmentOrder",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("organization_id", models.UUIDField(db_index=True)),
                (
                    "source",
                    models.CharField(
                        choices=[("erpnext", "ERPNext"), ("shopify", "Shopify")],
                        max_length=32,
                    ),
                ),
                ("order_id", models.CharField(max_length=191)),
                ("seller_company", models.CharField(max_length=140)),
                ("distributor_company", models.CharField(max_length=140)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("waiting_stock", "Waiting Stock"),
                            ("fulfilled", "Fulfilled"),
                            ("failed", "Failed"),
                            ("returned", "Returned"),
                        ],
                        default="pending",
                        max_length=32,
                    ),
                ),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("normalized_order", models.JSONField(blank=True, default=dict)),
                ("fulfillment_payload", models.JSONField(blank=True, default=dict)),
                ("result_payload", models.JSONField(blank=True, default=dict)),
                ("serial_numbers", models.JSONField(blank=True, default=list)),
                ("sales_order_name", models.CharField(blank=True, max_length=140)),
                ("delivery_note_name", models.CharField(blank=True, max_length=140)),
                ("delivery_note_submitted_at", models.DateTimeField(blank=True, null=True)),
                ("backorder_attempts", models.PositiveIntegerField(default=0)),
                ("last_error_code", models.CharField(blank=True, max_length=64)),
                ("last_error_message", models.TextField(blank=True)),
                ("next_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="fulfillmentitemmap",
            constraint=models.UniqueConstraint(
                fields=("organization_id", "source", "source_company", "source_item_code"),
                name="uniq_fmap_source_item",
            ),
        ),
        migrations.AddConstraint(
            model_name="fulfillmentorder",
            constraint=models.UniqueConstraint(
                fields=("organization_id", "source", "order_id"),
                name="uniq_fulfillment_order",
            ),
        ),
    ]
