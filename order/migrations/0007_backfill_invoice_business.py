from django.db import migrations


def forwards(apps, schema_editor):
    Invoice = apps.get_model("order", "Invoice")
    InvoiceAttachment = apps.get_model("order", "InvoiceAttachment")
    InvoiceLineItem = apps.get_model("order", "InvoiceLineItem")
    StudentFile = apps.get_model("agency_inventory", "StudentFile")
    Agency = apps.get_model("agency_inventory", "Agency")

    for invoice in Invoice.objects.filter(business_id__isnull=True).iterator():
        bid = None
        if invoice.student_id:
            bid = (
                StudentFile.objects.filter(pk=invoice.student_id)
                .values_list("business_id", flat=True)
                .first()
            )
        if not bid and invoice.agency_id:
            bid = (
                Agency.objects.filter(pk=invoice.agency_id)
                .values_list("business_id", flat=True)
                .first()
            )
        if bid:
            Invoice.objects.filter(pk=invoice.pk).update(business_id=bid)

    for att in InvoiceAttachment.objects.filter(business_id__isnull=True).iterator():
        inv = att.invoices.first()
        if inv and inv.business_id:
            InvoiceAttachment.objects.filter(pk=att.pk).update(business_id=inv.business_id)

    for line in InvoiceLineItem.objects.filter(business_id__isnull=True).select_related("invoice").iterator():
        if line.invoice_id and getattr(line.invoice, "business_id", None):
            InvoiceLineItem.objects.filter(pk=line.pk).update(business_id=line.invoice.business_id)


def noop_reverse(_apps, _schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0006_historicalinvoice_business_and_more"),
        ("agency_inventory", "0020_backfill_business_tenant_data"),
    ]

    operations = [
        migrations.RunPython(forwards, noop_reverse),
    ]
