from django.db import migrations


def backfill(apps, schema_editor):
    TicketReply = apps.get_model("support", "TicketReply")
    TicketAttachment = apps.get_model("support", "TicketAttachment")

    for reply in TicketReply.objects.filter(agency__isnull=True).select_related("ticket"):
        if reply.ticket_id and reply.ticket.agency_id:
            TicketReply.objects.filter(pk=reply.pk).update(agency_id=reply.ticket.agency_id)

    for att in TicketAttachment.objects.filter(agency__isnull=True).select_related("ticket", "reply__ticket"):
        ticket = att.ticket
        if ticket is None and att.reply_id:
            ticket = att.reply.ticket
        if ticket and ticket.agency_id:
            TicketAttachment.objects.filter(pk=att.pk).update(agency_id=ticket.agency_id)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("support", "0002_tenant_agency_scope"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
