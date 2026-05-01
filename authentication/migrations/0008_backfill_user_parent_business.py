from django.db import migrations


def forwards(apps, schema_editor):
    User = apps.get_model("authentication", "User")
    Agency = apps.get_model("agency_inventory", "Agency")
    StudentFile = apps.get_model("agency_inventory", "StudentFile")

    for user in User.objects.filter(parent_business_id__isnull=True).exclude(parent_agency_id__isnull=True).iterator():
        bid = (
            Agency.objects.filter(pk=user.parent_agency_id)
            .values_list("business_id", flat=True)
            .first()
        )
        if bid:
            User.objects.filter(pk=user.pk).update(parent_business_id=bid)

    for user in (
        User.objects.filter(parent_business_id__isnull=True)
        .exclude(linked_student_file_id__isnull=True)
        .iterator()
    ):
        bid = (
            StudentFile.objects.filter(pk=user.linked_student_file_id)
            .values_list("business_id", flat=True)
            .first()
        )
        if bid:
            User.objects.filter(pk=user.pk).update(parent_business_id=bid)


def noop_reverse(_apps, _schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0007_user_parent_business"),
        ("agency_inventory", "0020_backfill_business_tenant_data"),
    ]

    operations = [
        migrations.RunPython(forwards, noop_reverse),
    ]
