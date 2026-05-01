from django.db import migrations


def forwards(apps, schema_editor):
    Notification = apps.get_model("authentication", "Notification")
    User = apps.get_model("authentication", "User")

    for notification in Notification.objects.filter(business_id__isnull=True).iterator():
        business_id = None
        if notification.actor_id:
            business_id = (
                User.objects.filter(pk=notification.actor_id)
                .values_list("parent_business_id", flat=True)
                .first()
            )
        if not business_id and notification.recipient_id:
            business_id = (
                User.objects.filter(pk=notification.recipient_id)
                .values_list("parent_business_id", flat=True)
                .first()
            )
        if business_id:
            Notification.objects.filter(pk=notification.pk).update(business_id=business_id)


def noop_reverse(_apps, _schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0009_historicalnotification_business_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, noop_reverse),
    ]
