from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from agency_inventory.models import Agency, StudentFile
from authentication.base import BaseModel
from utils.slug_utils import generate_unique_code, generate_unique_slug

from .constants import InvoiceStatusChoice, RecipientTypeChoice


class InvoiceAttachment(BaseModel):
    title = models.CharField(max_length=255, blank=True, null=True)
    file_url = models.URLField(max_length=1000, blank=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or "Invoice attachment"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self.title or self.file_url or "invoice-attachment", self)
        super().save(*args, **kwargs)


class Invoice(BaseModel):
    invoice_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    issue_date = models.DateField()
    due_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=InvoiceStatusChoice.choices, default=InvoiceStatusChoice.DRAFT)

    recipient_type = models.CharField(
        max_length=20,
        choices=RecipientTypeChoice.choices,
        default=RecipientTypeChoice.CUSTOM,
    )
    agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, related_name="invoices", null=True, blank=True)
    student = models.ForeignKey(StudentFile, on_delete=models.SET_NULL, related_name="invoices", null=True, blank=True)
    custom_recipient_name = models.CharField(max_length=255, blank=True, null=True)
    custom_recipient_email = models.EmailField(blank=True, null=True)
    custom_recipient_phone = models.CharField(max_length=30, blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    attachments = models.ManyToManyField(InvoiceAttachment, related_name="invoices", blank=True)
    created_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.invoice_id or f"Invoice {self.id}"

    def clean(self):
        if self.due_date and self.issue_date and self.due_date < self.issue_date:
            raise ValidationError({"due_date": "Due date cannot be earlier than issue date."})

        if self.recipient_type == RecipientTypeChoice.AGENCY and not self.agency_id:
            raise ValidationError({"agency": "Agency is required for agency recipient type."})

        if self.recipient_type == RecipientTypeChoice.STUDENT and not self.student_id:
            raise ValidationError({"student": "Student is required for student recipient type."})

        if self.recipient_type == RecipientTypeChoice.CUSTOM and not self.custom_recipient_name:
            raise ValidationError({"custom_recipient_name": "Recipient name is required for custom recipient type."})

        if self.student_id and self.agency_id and self.student.agency_id and self.student.agency_id != self.agency_id:
            raise ValidationError({"agency": "Selected agency does not match the student's agency."})

    def save(self, *args, **kwargs):
        if not self.invoice_id:
            self.invoice_id = generate_unique_code(Invoice, field_name="invoice_id", prefix="INV", number_length=5)
        if not self.slug:
            self.slug = generate_unique_slug(f"{self.invoice_id}-{self.issue_date}", self)
        self.full_clean()
        super().save(*args, **kwargs)


class InvoiceLineItem(BaseModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.title} ({self.quantity} x {self.unit_price})"

    def save(self, *args, **kwargs):
        self.line_total = (self.unit_price or Decimal("0.00")) * Decimal(self.quantity or 0)
        super().save(*args, **kwargs)
