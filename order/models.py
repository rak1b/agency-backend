from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction

from agency_inventory.models import Agency, Business, StudentFile
from authentication.base import BaseModel
from utils.slug_utils import generate_unique_slug

from .constants import DiscountTypeChoice, InvoiceStatusChoice, RecipientTypeChoice


class InvoiceAttachment(BaseModel):
    """
    Scoped to the same agency as the invoice once the invoice is linked.
    """

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="invoice_attachments", null=True, blank=True)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="business_invoice_attachments", null=True, blank=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    file_url = models.URLField(max_length=1000, blank=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or "Invoice attachment"

    def save(self, *args, **kwargs):
        # Linked through M2M ``Invoice.attachments``; resolve agency from any parent invoice.
        if self.pk:
            parent_invoice = self.invoices.select_related("agency").first()
            if parent_invoice and parent_invoice.agency_id:
                self.agency_id = parent_invoice.agency_id
            if self.business_id is None and parent_invoice and getattr(parent_invoice, "business_id", None):
                self.business_id = parent_invoice.business_id
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
    business = models.ForeignKey(Business, on_delete=models.SET_NULL, related_name="business_invoices", null=True, blank=True)
    student = models.ForeignKey(StudentFile, on_delete=models.SET_NULL, related_name="invoices", null=True, blank=True)
    custom_recipient_name = models.CharField(max_length=255, blank=True, null=True)
    custom_recipient_email = models.EmailField(blank=True, null=True)
    custom_recipient_phone = models.CharField(max_length=30, blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountTypeChoice.choices,
        default=DiscountTypeChoice.FLAT,
    )
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    attachments = models.ManyToManyField(InvoiceAttachment, related_name="invoices", blank=True)
    created_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True)
    is_created_by_business_owner = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "True when the invoice was created by business-tier staff (AGENCY_SUPER_ADMIN or "
            "AGENCY_EMPLOYEE). They only list invoices with this flag; B2B-issued invoices stay False."
        ),
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.invoice_id or f"Invoice {self.id}"

    @classmethod
    def _generate_next_invoice_id(cls):
        """
        Generate invoice ids using ``all_objects`` so soft-deleted invoices are also
        considered and uniqueness collisions are avoided.
        """
        prefix = "INV"
        number_length = 5
        with transaction.atomic():
            last_invoice = (
                cls.all_objects.select_for_update()
                .filter(invoice_id__startswith=prefix)
                .order_by("-invoice_id")
                .first()
            )
            if last_invoice and last_invoice.invoice_id:
                last_number = int(last_invoice.invoice_id[len(prefix):])
            else:
                last_number = 0
            return f"{prefix}{(last_number + 1):0{number_length}d}"

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

        if self.discount_amount < 0:
            raise ValidationError({"discount_amount": "Discount amount cannot be negative."})

        if self.discount_type == DiscountTypeChoice.PERCENTAGE and self.discount_amount > 100:
            raise ValidationError({"discount_amount": "Percentage discount must be between 0 and 100."})

    def save(self, *args, **kwargs):
        if not self.invoice_id:
            self.invoice_id = self._generate_next_invoice_id()
        if not self.slug:
            self.slug = generate_unique_slug(f"{self.invoice_id}-{self.issue_date}", self)
        if self.business_id is None:
            if self.student_id:
                bid = StudentFile.objects.filter(pk=self.student_id).values_list("business_id", flat=True).first()
                if bid:
                    self.business_id = bid
            elif self.agency_id:
                bid = Agency.objects.filter(pk=self.agency_id).values_list("business_id", flat=True).first()
                if bid:
                    self.business_id = bid
        self.full_clean()
        super().save(*args, **kwargs)


class InvoiceLineItem(BaseModel):
    agency = models.ForeignKey(
        Agency,
        on_delete=models.CASCADE,
        related_name="invoice_line_items",
        null=True,
        blank=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="business_invoice_line_items",
        null=True,
        blank=True,
    )
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.title} ({self.amount})"

    def save(self, *args, **kwargs):
        if self.invoice_id and self.invoice.agency_id:
            self.agency_id = self.invoice.agency_id
        if self.business_id is None and self.invoice_id and getattr(self.invoice, "business_id", None):
            self.business_id = self.invoice.business_id
        super().save(*args, **kwargs)
