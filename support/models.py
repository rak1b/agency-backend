from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from agency_inventory.models import Agency, StudentFile
from authentication.base import BaseModel
from utils.slug_utils import generate_unique_slug

from .constants import TicketCreatorTypeChoice, TicketPriorityChoice, TicketStatusChoice


class Ticket(BaseModel):
    ticket_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=TicketStatusChoice.choices, default=TicketStatusChoice.OPEN)
    priority = models.CharField(max_length=20, choices=TicketPriorityChoice.choices, default=TicketPriorityChoice.MEDIUM)
    category = models.CharField(max_length=120, blank=True, null=True)

    created_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True)
    creator_type = models.CharField(
        max_length=20,
        choices=TicketCreatorTypeChoice.choices,
    )
    agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, related_name="support_tickets", null=True, blank=True)
    student_file = models.ForeignKey(
        StudentFile,
        on_delete=models.SET_NULL,
        related_name="support_tickets",
        null=True,
        blank=True,
    )

    last_replied_at = models.DateTimeField(null=True, blank=True)
    last_reply_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        related_name="ticket_last_replies",
        null=True,
        blank=True,
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.ticket_id or f"Ticket {self.id}"

    @classmethod
    def _generate_next_ticket_id(cls):
        prefix = "TIC"
        number_length = 6
        with transaction.atomic():
            last_ticket = (
                cls.all_objects.select_for_update()
                .filter(ticket_id__startswith=prefix)
                .order_by("-ticket_id")
                .first()
            )
            if last_ticket and last_ticket.ticket_id:
                last_number = int(last_ticket.ticket_id[len(prefix):])
            else:
                last_number = 0
            return f"{prefix}{(last_number + 1):0{number_length}d}"

    def clean(self):
        if self.creator_type == TicketCreatorTypeChoice.AGENCY and not self.agency_id:
            raise ValidationError({"agency": "Agency is required for agency-created tickets."})
        if self.creator_type == TicketCreatorTypeChoice.STUDENT and not self.student_file_id:
            raise ValidationError({"student_file": "Student file is required for student-created tickets."})
        if (
            self.student_file_id
            and self.agency_id
            and self.student_file.agency_id
            and self.student_file.agency_id != self.agency_id
        ):
            raise ValidationError({"agency": "Agency does not match selected student file agency."})

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            self.ticket_id = self._generate_next_ticket_id()
        if not self.slug:
            self.slug = generate_unique_slug(f"{self.ticket_id}-{self.subject}", self)
        if self.status in {TicketStatusChoice.SOLVED, TicketStatusChoice.CLOSED} and not self.resolved_at:
            self.resolved_at = timezone.now()
        elif self.status not in {TicketStatusChoice.SOLVED, TicketStatusChoice.CLOSED}:
            self.resolved_at = None
        self.full_clean()
        super().save(*args, **kwargs)


class TicketReply(BaseModel):
    """
    One message thread entry on a ticket.

    Reply files are ``TicketAttachment`` rows with ``reply`` set; the FK uses
    ``related_name="attachments"``, so use ``reply.attachments`` (reverse FK).
    Do not add a separate ``ManyToManyField`` here: it would clash with that
    reverse accessor and duplicate the same relationship.
    """

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="replies")
    message = models.TextField(blank=True, null=True)
    replied_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply #{self.id} on {self.ticket.ticket_id}"


class TicketAttachment(BaseModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="attachments", null=True, blank=True)
    reply = models.ForeignKey(TicketReply, on_delete=models.CASCADE, related_name="attachments", null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_url = models.URLField(max_length=1000)
    uploaded_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.file_name or self.file_url

    def clean(self):
        if not self.ticket_id and not self.reply_id:
            raise ValidationError("Attachment must belong to either a ticket or a reply.")
