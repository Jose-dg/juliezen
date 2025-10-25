from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("erpnext", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="erpnextcredential",
            name="company",
            field=models.CharField(
                blank=True,
                default="",
                help_text="ERPNext company that these credentials operate on; leave blank if shared.",
                max_length=140,
                verbose_name="Company",
            ),
        ),
        migrations.AddIndex(
            model_name="erpnextcredential",
            index=models.Index(fields=("organization_id", "company"), name="idx_erpnext_org_company"),
        ),
    ]
