from django.db import models
from django.utils.translation import gettext_lazy as _


class RecipientTypeChoice(models.TextChoices):
    AGENCY = "agency", _("Agency")
    STUDENT = "student", _("Student")
    CUSTOM = "custom", _("Custom")


class InvoiceStatusChoice(models.TextChoices):
    DRAFT = "draft", _("Draft")
    SENT = "sent", _("Sent")
    PAID = "paid", _("Paid")
    CANCELLED = "cancelled", _("Cancelled")


class DiscountTypeChoice(models.TextChoices):
    FLAT = "flat", _("Flat")
    PERCENTAGE = "percentage", _("Percentage")
