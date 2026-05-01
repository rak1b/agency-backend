from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from agency_inventory.models import _agency_business_pk

from authentication.tenant_utils import (
    invoice_issuer_agency_stamp_id,
    tenant_business_id,
    user_is_master_admin,
)

from ...constants import DiscountTypeChoice, InvoiceStatusChoice, RecipientTypeChoice
from ...models import Invoice, InvoiceAttachment, InvoiceLineItem


class InvoiceAttachmentPayloadSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    title = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)


class InvoiceLineItemPayloadSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    title = serializers.CharField(required=True, max_length=255)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"))


class InvoiceSerializer(serializers.ModelSerializer):
    agency_name = serializers.CharField(source="agency.name", read_only=True)
    student_name = serializers.SerializerMethodField(read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    attachments = InvoiceAttachmentPayloadSerializer(many=True, write_only=True, required=False)
    attachment_details = serializers.SerializerMethodField(read_only=True)
    invoice_items = InvoiceLineItemPayloadSerializer(many=True, source="line_items", write_only=True, required=False)
    invoice_item_details = serializers.SerializerMethodField(read_only=True)
    agency_details = serializers.SerializerMethodField(read_only=True)
    student_details = serializers.SerializerMethodField(read_only=True)
    created_by_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Invoice
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = [
            "invoice_id",
            "slug",
            "subtotal",
            "total_amount",
            "created_at",
            "updated_at",
            "created_by",
            "agency_name",
            "student_name",
            "created_by_name",
            "agency_details",
            "student_details",
            "created_by_details",
            "attachment_details",
            "invoice_item_details",
        ]

    def to_internal_value(self, data):
        """
        Backward compatibility: accept legacy ``line_items`` payload key and map it
        to the current ``invoice_items`` key.
        """
        if isinstance(data, dict) and "line_items" in data and "invoice_items" not in data:
            data = data.copy()
            data["invoice_items"] = data.get("line_items")
        return super().to_internal_value(data)

    def get_student_name(self, obj):
        if not obj.student:
            return None
        return f"{obj.student.given_name} {obj.student.surname}".strip()

    def get_attachment_details(self, obj):
        return [
            {
                "id": attachment.id,
                "title": attachment.title,
                "file_url": attachment.file_url,
                "slug": attachment.slug,
            }
            for attachment in obj.attachments.all()
        ]

    def get_invoice_item_details(self, obj):
        return [
            {
                "id": item.id,
                "title": item.title,
                "amount": item.amount,
            }
            for item in obj.line_items.all()
        ]

    def get_agency_details(self, obj):
        if not obj.agency:
            return None
        return {
            "id": obj.agency.id,
            "name": obj.agency.name,
            "slug": obj.agency.slug,
            "status": obj.agency.status,
            "business_email": obj.agency.business_email,
            "phone": obj.agency.phone,
        }

    def get_student_details(self, obj):
        if not obj.student:
            return None
        return {
            "id": obj.student.id,
            "student_file_id": obj.student.student_file_id,
            "slug": obj.student.slug,
            "given_name": obj.student.given_name,
            "surname": obj.student.surname,
            "passport_number": obj.student.passport_number,
            "agency_id": obj.student.agency_id,
        }

    def get_created_by_details(self, obj):
        if not obj.created_by:
            return None
        return {
            "id": obj.created_by.id,
            "name": getattr(obj.created_by, "name", None),
            "email": getattr(obj.created_by, "email", None),
        }

    def validate(self, attrs):
        recipient_type = attrs.get("recipient_type", getattr(self.instance, "recipient_type", None))
        agency = attrs.get("agency", getattr(self.instance, "agency", None))
        student = attrs.get("student", getattr(self.instance, "student", None))
        custom_name = attrs.get("custom_recipient_name", getattr(self.instance, "custom_recipient_name", None))
        issue_date = attrs.get("issue_date", getattr(self.instance, "issue_date", None))
        due_date = attrs.get("due_date", getattr(self.instance, "due_date", None))
        discount_type = attrs.get("discount_type", getattr(self.instance, "discount_type", DiscountTypeChoice.FLAT))
        discount_amount = attrs.get("discount_amount", getattr(self.instance, "discount_amount", Decimal("0.00")))

        if due_date and issue_date and due_date < issue_date:
            raise serializers.ValidationError({"due_date": "Due date cannot be earlier than issue date."})

        if discount_amount is not None and discount_amount < 0:
            raise serializers.ValidationError({"discount_amount": "Discount amount cannot be negative."})

        if discount_type == DiscountTypeChoice.PERCENTAGE and discount_amount is not None and discount_amount > 100:
            raise serializers.ValidationError({"discount_amount": "Percentage discount must be between 0 and 100."})

        if recipient_type == RecipientTypeChoice.AGENCY:
            if not agency:
                raise serializers.ValidationError({"agency": "Agency is required for recipient type 'agency'."})

        elif recipient_type == RecipientTypeChoice.STUDENT:
            if not student:
                raise serializers.ValidationError({"student": "Student is required for recipient type 'student'."})
            if student and agency and student.agency_id and student.agency_id != agency.id:
                raise serializers.ValidationError({"agency": "Selected agency does not match the student's agency."})

        elif recipient_type == RecipientTypeChoice.CUSTOM:
            if not custom_name:
                raise serializers.ValidationError(
                    {"custom_recipient_name": "Custom recipient name is required for recipient type 'custom'."}
                )

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated and not user_is_master_admin(user):
            tenant_bid = tenant_business_id(user)
            if tenant_bid:
                if agency:
                    aid = _agency_business_pk(agency)
                if student:
                    st_bid = getattr(student, "business_id", None) or _agency_business_pk(
                        getattr(student, "agency_id", None)
                    )
                    if st_bid and st_bid != tenant_bid:
                        raise serializers.ValidationError({"student": "Student must belong to your business."})

        return attrs

    def _normalize_recipient_data(self, validated_data):
        """
        Keep recipient fields consistent with selected recipient type.
        """
        recipient_type = validated_data.get("recipient_type")
        request = self.context.get("request")
        user = getattr(request, "user", None)
        force_tenant = user and user.is_authenticated and not user_is_master_admin(user)

        if recipient_type == RecipientTypeChoice.AGENCY:
            agency_inst = validated_data.get("agency")
            if not force_tenant and agency_inst and getattr(agency_inst, "business_id", None):
                validated_data["business"] = agency_inst.business
            validated_data["student"] = None
            validated_data["custom_recipient_name"] = None
            validated_data["custom_recipient_email"] = None
            validated_data["custom_recipient_phone"] = None
        elif recipient_type == RecipientTypeChoice.STUDENT:
            student = validated_data.get("student")
            if student and student.agency_id:
                # Keep agency synced from student to avoid cross-agency mismatch.
                validated_data["agency"] = student.agency
            elif force_tenant and user:
                # Student file may exist without an agency FK; still stamp issuer context.
                stamp = invoice_issuer_agency_stamp_id(user)
                if stamp:
                    validated_data["agency_id"] = stamp
            if not force_tenant and student and getattr(student, "business_id", None):
                validated_data["business"] = getattr(student, "business", None)
            validated_data["custom_recipient_name"] = None
            validated_data["custom_recipient_email"] = None
            validated_data["custom_recipient_phone"] = None
        elif recipient_type == RecipientTypeChoice.CUSTOM:
            # Stamp business; stamp agency from issuer (B2B or ``parent_agency``) for API scoping and reporting.
            validated_data.pop("agency", None)
            validated_data.pop("agency_id", None)
            validated_data.pop("business", None)
            user = getattr(self.context.get("request"), "user", None)
            validated_data["student"] = None
            if user and user.is_authenticated and not user_is_master_admin(user):
                tenant_bid = tenant_business_id(user)
                if tenant_bid:
                    validated_data["business_id"] = tenant_bid
                stamp = invoice_issuer_agency_stamp_id(user)
                if stamp:
                    validated_data["agency_id"] = stamp

    def _upsert_attachments(self, invoice, attachments_data):
        attachment_ids = []
        for row in attachments_data:
            attachment_id = row.get("id")
            title = row.get("title")
            file_url = row.get("file_url")

            if attachment_id:
                try:
                    attachment = InvoiceAttachment.objects.get(id=attachment_id)
                except InvoiceAttachment.DoesNotExist:
                    raise serializers.ValidationError({"attachments": f"Attachment id {attachment_id} does not exist."})
                attachment.title = title if title is not None else attachment.title
                attachment.file_url = file_url if file_url is not None else attachment.file_url
                attachment.save()
            else:
                attachment = InvoiceAttachment.objects.create(
                    title=title,
                    file_url=file_url,
                    agency=invoice.agency,
                    business=getattr(invoice, "business", None),
                )
            attachment_ids.append(attachment.id)
        invoice.attachments.set(attachment_ids)
        for attachment in invoice.attachments.all():
            attachment.save()

    def _upsert_line_items(self, invoice, line_items_data):
        retained_item_ids = []
        for row in line_items_data:
            line_item_id = row.get("id")
            if line_item_id:
                try:
                    line_item = InvoiceLineItem.objects.get(id=line_item_id, invoice=invoice)
                except InvoiceLineItem.DoesNotExist:
                    raise serializers.ValidationError(
                        {"invoice_items": f"Invoice item id {line_item_id} does not exist for this invoice."}
                    )
                line_item.title = row.get("title", line_item.title)
                line_item.amount = row.get("amount", line_item.amount)
                line_item.save()
            else:
                line_item = InvoiceLineItem.objects.create(
                    invoice=invoice,
                    title=row["title"],
                    amount=row.get("amount", Decimal("0.00")),
                )
            retained_item_ids.append(line_item.id)

        # Replace strategy: any item not sent in payload is removed.
        invoice.line_items.exclude(id__in=retained_item_ids).delete()

    def _refresh_totals(self, invoice):
        subtotal = invoice.line_items.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        discount_amount = invoice.discount_amount or Decimal("0.00")
        vat_amount = invoice.vat_amount or Decimal("0.00")

        if invoice.discount_type == DiscountTypeChoice.PERCENTAGE:
            discount_value = (subtotal * discount_amount) / Decimal("100.00")
        else:
            discount_value = discount_amount

        total_amount = subtotal - discount_value + vat_amount
        if total_amount < 0:
            total_amount = Decimal("0.00")

        invoice.subtotal = subtotal
        invoice.total_amount = total_amount
        invoice.save(update_fields=["subtotal", "total_amount", "updated_at"])

    @transaction.atomic
    def create(self, validated_data):
        attachments_data = validated_data.pop("attachments", [])
        invoice_items_data = validated_data.pop("line_items", [])

        self._normalize_recipient_data(validated_data)

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user

        invoice = Invoice.objects.create(**validated_data)

        if attachments_data:
            self._upsert_attachments(invoice, attachments_data)
        if invoice_items_data:
            self._upsert_line_items(invoice, invoice_items_data)

        self._refresh_totals(invoice)
        return invoice

    @transaction.atomic
    def update(self, instance, validated_data):
        attachments_data = validated_data.pop("attachments", None)
        invoice_items_data = validated_data.pop("line_items", None)

        self._normalize_recipient_data(validated_data)

        invoice = super().update(instance, validated_data)

        if attachments_data is not None:
            self._upsert_attachments(invoice, attachments_data)
        if invoice_items_data is not None:
            self._upsert_line_items(invoice, invoice_items_data)

        self._refresh_totals(invoice)
        return invoice


class InvoiceReportQuerySerializer(serializers.Serializer):
    """Optional query params for GET ``/invoices/report/``."""

    issue_date_from = serializers.DateField(required=False)
    issue_date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        start = attrs.get("issue_date_from")
        end = attrs.get("issue_date_to")
        if start and end and end < start:
            raise serializers.ValidationError("issue_date_to cannot be before issue_date_from.")
        return attrs


class InvoiceReportSummarySerializer(serializers.Serializer):
    invoice_count = serializers.IntegerField()
    subtotal_sum = serializers.DecimalField(max_digits=12, decimal_places=2)
    vat_amount_sum = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_amount_sum = serializers.DecimalField(max_digits=12, decimal_places=2)


class InvoiceReportBreakdownRowSerializer(serializers.Serializer):
    """One bucket in a grouped aggregate (e.g. all invoices in ``draft``)."""

    key = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class InvoiceReportResponseSerializer(serializers.Serializer):
    filters = serializers.DictField()
    summary = InvoiceReportSummarySerializer()
    by_status = InvoiceReportBreakdownRowSerializer(many=True)
    by_recipient_type = InvoiceReportBreakdownRowSerializer(many=True)
