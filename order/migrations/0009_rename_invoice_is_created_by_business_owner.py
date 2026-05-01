# Generated manually: rename Invoice origin flag column.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0008_invoice_is_created_by_agency_owner"),
    ]

    operations = [
        migrations.RenameField(
            model_name="invoice",
            old_name="is_created_by_agency_owner",
            new_name="is_created_by_business_owner",
        ),
        migrations.RenameField(
            model_name="historicalinvoice",
            old_name="is_created_by_agency_owner",
            new_name="is_created_by_business_owner",
        ),
    ]
