from django.db import migrations


def backfill(apps, schema_editor):
    InvoiceAttachment = apps.get_model("order", "InvoiceAttachment")
    InvoiceLineItem = apps.get_model("order", "InvoiceLineItem")

    for att in InvoiceAttachment.objects.filter(agency__isnull=True):
        inv = att.invoices.order_by("pk").first()
        if inv and inv.agency_id:
            InvoiceAttachment.objects.filter(pk=att.pk).update(agency_id=inv.agency_id)

    for line in InvoiceLineItem.objects.filter(agency__isnull=True).select_related("invoice"):
        if line.invoice_id and line.invoice.agency_id:
            InvoiceLineItem.objects.filter(pk=line.pk).update(agency_id=line.invoice.agency_id)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0004_tenant_agency_scope"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
