from django.db import models
from django.utils.translation import gettext_lazy as _


class TicketStatusChoice(models.TextChoices):
    OPEN = "open", _("Open")
    PENDING = "pending", _("Pending")
    IN_PROGRESS = "in_progress", _("In Progress")
    SOLVED = "solved", _("Solved")
    CLOSED = "closed", _("Closed")


class TicketPriorityChoice(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    URGENT = "urgent", _("Urgent")


class TicketCreatorTypeChoice(models.TextChoices):
    AGENCY = "agency", _("Agency")
    STUDENT = "student", _("Student")
