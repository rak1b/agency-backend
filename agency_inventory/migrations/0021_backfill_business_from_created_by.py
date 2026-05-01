from django.db import migrations


def forwards(apps, schema_editor):
    business_scoped_models = [
        "Agency",
        "Customer",
        "StudentFile",
        "OfficeCost",
        "StudentCost",
    ]

    for model_name in business_scoped_models:
        model = apps.get_model("agency_inventory", model_name)
        if not any(field.name == "created_by" for field in model._meta.fields):
            continue
        rows = model.objects.filter(business_id__isnull=True).exclude(created_by_id__isnull=True)
        for row in rows.select_related("created_by").iterator():
            business_id = getattr(row.created_by, "parent_business_id", None)
            if business_id:
                model.objects.filter(pk=row.pk).update(business_id=business_id)


def noop_reverse(_apps, _schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("agency_inventory", "0020_backfill_business_tenant_data"),
        ("authentication", "0010_backfill_notification_business"),
    ]

    operations = [
        migrations.RunPython(forwards, noop_reverse),
    ]
