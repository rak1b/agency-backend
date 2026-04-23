import os
import re
import uuid
from datetime import datetime

from django.db import transaction
from rest_framework import serializers

from authentication.constants import UserTypeChoice
from utils.cloudflare_minio_utils import upload_file_to_r2

from ...constants import TicketCreatorTypeChoice, TicketPriorityChoice, TicketStatusChoice
from ...models import Ticket, TicketAttachment, TicketReply


class TicketAttachmentPayloadSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    file_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file_url = serializers.URLField(required=True)


class TicketReplyPayloadSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    attachments = TicketAttachmentPayloadSerializer(many=True, required=False)

    def validate(self, attrs):
        message = attrs.get("message")
        attachments = attrs.get("attachments", [])
        request = self.context.get("request")
        uploaded_files = request.FILES.getlist("attachments_files") if request else []
        if not message and not attachments and not uploaded_files:
            raise serializers.ValidationError("Reply must include either message text or at least one attachment.")
        return attrs


class TicketSerializer(serializers.ModelSerializer):
    attachments = TicketAttachmentPayloadSerializer(many=True, write_only=True, required=False)
    attachment_details = serializers.SerializerMethodField(read_only=True)
    reply_details = serializers.SerializerMethodField(read_only=True)
    agency_details = serializers.SerializerMethodField(read_only=True)
    student_file_details = serializers.SerializerMethodField(read_only=True)
    created_by_details = serializers.SerializerMethodField(read_only=True)
    last_reply_by_details = serializers.SerializerMethodField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    priority_label = serializers.CharField(source="get_priority_display", read_only=True)

    class Meta:
        model = Ticket
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = [
            "ticket_id",
            "slug",
            "created_by",
            "creator_type",
            "last_replied_at",
            "last_reply_by",
            "resolved_at",
            "attachment_details",
            "reply_details",
            "agency_details",
            "student_file_details",
            "created_by_details",
            "last_reply_by_details",
            "status_label",
            "priority_label",
            "created_at",
            "updated_at",
        ]

    def get_attachment_details(self, obj):
        return [
            {
                "id": attachment.id,
                "file_name": attachment.file_name,
                "file_url": attachment.file_url,
                "uploaded_by_id": attachment.uploaded_by_id,
                "created_at": attachment.created_at,
            }
            for attachment in obj.attachments.all()
        ]

    def get_reply_details(self, obj):
        return [
            {
                "id": reply.id,
                "message": reply.message,
                "replied_by_id": reply.replied_by_id,
                "replied_by_name": getattr(reply.replied_by, "name", None),
                "created_at": reply.created_at,
                "attachments": [
                    {
                        "id": attachment.id,
                        "file_name": attachment.file_name,
                        "file_url": attachment.file_url,
                    }
                    for attachment in reply.attachments.all()
                ],
            }
            for reply in obj.replies.select_related("replied_by").prefetch_related("attachments").all()
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

    def get_student_file_details(self, obj):
        if not obj.student_file:
            return None
        return {
            "id": obj.student_file.id,
            "student_file_id": obj.student_file.student_file_id,
            "slug": obj.student_file.slug,
            "given_name": obj.student_file.given_name,
            "surname": obj.student_file.surname,
            "agency_id": obj.student_file.agency_id,
        }

    def get_created_by_details(self, obj):
        if not obj.created_by:
            return None
        return {
            "id": obj.created_by.id,
            "name": obj.created_by.name,
            "email": obj.created_by.email,
            "user_type": obj.created_by.user_type,
        }

    def get_last_reply_by_details(self, obj):
        if not obj.last_reply_by:
            return None
        return {
            "id": obj.last_reply_by.id,
            "name": obj.last_reply_by.name,
            "email": obj.last_reply_by.email,
        }

    def _resolve_creator_type(self, user):
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authenticated user is required.")

        student_role_exists = user.role.filter(name__icontains="student").exists()
        if student_role_exists:
            return TicketCreatorTypeChoice.STUDENT

        agency_user_types = {
            UserTypeChoice.AGENCY_SUPER_ADMIN,
            UserTypeChoice.AGENCY_EMPLOYEE,
            UserTypeChoice.B2B_AGENT,
            UserTypeChoice.B2B_AGENT_EMPLOYEE,
        }
        if user.user_type in agency_user_types:
            return TicketCreatorTypeChoice.AGENCY

        role_names = [name.lower() for name in user.role.values_list("name", flat=True)]
        if any("agency" in role_name or "agent" in role_name for role_name in role_names):
            return TicketCreatorTypeChoice.AGENCY

        raise serializers.ValidationError(
            "Unable to determine ticket creator type from user role. Ensure role/user_type includes agency or student."
        )

    def _normalize_ticket_ownership(self, validated_data, creator_type, request_user):
        """
        Keep ticket owner relations consistent with creator type.
        """
        if creator_type == TicketCreatorTypeChoice.AGENCY:
            if not validated_data.get("agency") and request_user.parent_agency_id:
                validated_data["agency"] = request_user.parent_agency
            validated_data["student_file"] = None
        elif creator_type == TicketCreatorTypeChoice.STUDENT:
            student_file = validated_data.get("student_file")
            if not student_file:
                raise serializers.ValidationError(
                    {"student_file": "Student ticket requires `student_file`."}
                )
            validated_data["agency"] = student_file.agency

    def _normalize_upload_name(self, original_name):
        name_without_ext, extension = os.path.splitext(original_name or "")
        safe_name = re.sub(r"\s+", "_", (name_without_ext or "support-file").strip())
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "", safe_name) or "support-file"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_part = uuid.uuid4().hex[:6]
        return f"{safe_name}_{timestamp}_{unique_part}{extension}"

    def _create_attachments_from_payload_and_files(self, *, ticket=None, reply=None, attachment_rows=None):
        request = self.context.get("request")
        current_user = getattr(request, "user", None)

        attachment_rows = attachment_rows or []
        for row in attachment_rows:
            TicketAttachment.objects.create(
                ticket=ticket,
                reply=reply,
                file_name=row.get("file_name"),
                file_url=row["file_url"],
                uploaded_by=current_user,
            )

        if request:
            for uploaded_file in request.FILES.getlist("attachments_files"):
                uploaded_file.name = self._normalize_upload_name(uploaded_file.name)
                uploaded_file_url = upload_file_to_r2(uploaded_file)
                if uploaded_file_url:
                    TicketAttachment.objects.create(
                        ticket=ticket,
                        reply=reply,
                        file_name=uploaded_file.name,
                        file_url=uploaded_file_url,
                        uploaded_by=current_user,
                    )

    def validate(self, attrs):
        status = attrs.get("status", getattr(self.instance, "status", TicketStatusChoice.OPEN))
        priority = attrs.get("priority", getattr(self.instance, "priority", TicketPriorityChoice.MEDIUM))
        if status not in TicketStatusChoice.values:
            raise serializers.ValidationError({"status": "Invalid ticket status."})
        if priority not in TicketPriorityChoice.values:
            raise serializers.ValidationError({"priority": "Invalid ticket priority."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        attachments_data = validated_data.pop("attachments", [])
        request = self.context.get("request")
        request_user = getattr(request, "user", None)

        creator_type = self._resolve_creator_type(request_user)
        self._normalize_ticket_ownership(validated_data, creator_type, request_user)

        validated_data["created_by"] = request_user
        validated_data["creator_type"] = creator_type
        ticket = Ticket.objects.create(**validated_data)
        self._create_attachments_from_payload_and_files(ticket=ticket, attachment_rows=attachments_data)
        return ticket

    @transaction.atomic
    def update(self, instance, validated_data):
        attachments_data = validated_data.pop("attachments", None)
        request = self.context.get("request")
        request_user = getattr(request, "user", None)

        # Ownership should remain role-driven on edit as well.
        creator_type = self._resolve_creator_type(request_user)
        self._normalize_ticket_ownership(validated_data, creator_type, request_user)
        validated_data["creator_type"] = creator_type

        ticket = super().update(instance, validated_data)

        if attachments_data is not None:
            ticket.attachments.all().delete()
            self._create_attachments_from_payload_and_files(ticket=ticket, attachment_rows=attachments_data)

        return ticket

    @transaction.atomic
    def create_reply(self, ticket, validated_data):
        request = self.context.get("request")
        request_user = getattr(request, "user", None)
        message = validated_data.get("message")
        attachment_rows = validated_data.get("attachments", [])

        reply = TicketReply.objects.create(
            ticket=ticket,
            message=message,
            replied_by=request_user,
        )
        self._create_attachments_from_payload_and_files(reply=reply, attachment_rows=attachment_rows)

        ticket.last_replied_at = reply.created_at
        ticket.last_reply_by = request_user
        if ticket.status == TicketStatusChoice.OPEN:
            ticket.status = TicketStatusChoice.IN_PROGRESS
        ticket.save(update_fields=["last_replied_at", "last_reply_by", "status", "updated_at"])
        return reply
