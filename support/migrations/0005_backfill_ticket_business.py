from django.db import migrations


def forwards(apps, schema_editor):
    Ticket = apps.get_model("support", "Ticket")
    TicketReply = apps.get_model("support", "TicketReply")
    TicketAttachment = apps.get_model("support", "TicketAttachment")
    StudentFile = apps.get_model("agency_inventory", "StudentFile")
    Agency = apps.get_model("agency_inventory", "Agency")

    for ticket in Ticket.objects.filter(business_id__isnull=True).iterator():
        bid = None
        if ticket.student_file_id:
            bid = (
                StudentFile.objects.filter(pk=ticket.student_file_id)
                .values_list("business_id", flat=True)
                .first()
            )
        if not bid and ticket.agency_id:
            bid = (
                Agency.objects.filter(pk=ticket.agency_id)
                .values_list("business_id", flat=True)
                .first()
            )
        if bid:
            Ticket.objects.filter(pk=ticket.pk).update(business_id=bid)

    for reply in TicketReply.objects.filter(business_id__isnull=True).select_related("ticket").iterator():
        if reply.ticket_id and getattr(reply.ticket, "business_id", None):
            TicketReply.objects.filter(pk=reply.pk).update(business_id=reply.ticket.business_id)

    for att in TicketAttachment.objects.filter(business_id__isnull=True).iterator():
        ticket = att.ticket
        if ticket is None and att.reply_id:
            rel = TicketReply.objects.filter(pk=att.reply_id).select_related("ticket").first()
            ticket = rel.ticket if rel else None
        if ticket and getattr(ticket, "business_id", None):
            TicketAttachment.objects.filter(pk=att.pk).update(business_id=ticket.business_id)


def noop_reverse(_apps, _schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("support", "0004_historicalticket_business_and_more"),
        ("agency_inventory", "0020_backfill_business_tenant_data"),
    ]

    operations = [
        migrations.RunPython(forwards, noop_reverse),
    ]
