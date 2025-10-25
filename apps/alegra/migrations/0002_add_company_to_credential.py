from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alegra", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="alegracredential",
            name="company",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Compañía de ERPNext asociada a estas credenciales de Alegra.",
                max_length=140,
            ),
        ),
        migrations.AddIndex(
            model_name="alegracredential",
            index=models.Index(fields=("organization_id", "company"), name="idx_alegra_org_company"),
        ),
    ]
