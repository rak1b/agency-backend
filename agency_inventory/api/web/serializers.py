from rest_framework import serializers

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from authentication import constants as auth_constants
from authentication.models import User
from authentication.utils import email_utils
from authentication.tenant_utils import (
    is_student_portal_user,
    tenant_business_id,
    user_is_master_admin,
)

from ...models import (
    Agency,
    AppliedUniversity,
    Business,
    Country,
    Customer,
    OfficeCost,
    Program,
    StudentFile,
    StudentFileAttachment,
    StudentCost,
    University,
    UniversityIntake,
    UniversityProgram,
    UniversityProgramSubject,
    _agency_business_pk,
)
from ...constants import GenderChoice, ReviewStatusChoice
from ...services.application_progress import STEP_KEYS


def _ensure_agency_in_tenant_business(serializer, agency):
    """
    When BaseModelViewSet forces ``business_id`` from the tenant, model ``save()`` no longer
    overwrites it from ``agency``. Reject mismatched agencies here so rows cannot straddle tenants.
    """
    request = serializer.context.get("request")
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or user_is_master_admin(user):
        return
    tenant_bid = tenant_business_id(user)
    if not tenant_bid or agency is None:
        return
    agency_bid = _agency_business_pk(agency)


class AgencySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    active_customer_count = serializers.IntegerField(source="customers.count", read_only=True)

    class Meta:
        model = Agency
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at", "created_by", "created_by_name", "active_customer_count"]

    def validate(self, attrs):
        start_date = attrs.get("contract_start_date", getattr(self.instance, "contract_start_date", None))
        end_date = attrs.get("contract_end_date", getattr(self.instance, "contract_end_date", None))
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Contract end date must be later than start date.")
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at"]

    def validate(self, attrs):
        agency = attrs.get("agency", getattr(self.instance, "agency", None))
        _ensure_agency_in_tenant_business(self, agency)
        return attrs


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at"]

    def validate(self, attrs):
        agency = attrs.get("agency", getattr(self.instance, "agency", None))
        _ensure_agency_in_tenant_business(self, agency)
        return attrs


class InventoryDashboardQuerySerializer(serializers.Serializer):
    """
    Optional filters for the inventory dashboard.
    """

    agency = serializers.PrimaryKeyRelatedField(
        queryset=Agency.objects.all(),
        required=False,
        allow_null=True,
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({"end_date": "End date must be later than or equal to start date."})

        return attrs


class CustomerSerializer(serializers.ModelSerializer):
    agency_name = serializers.CharField(source="agency.name", read_only=True)
    assigned_counselor_name = serializers.CharField(source="assigned_counselor.name", read_only=True)

    class Meta:
        model = Customer
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = [
            "customer_id",
            "slug",
            "created_at",
            "updated_at",
            "agency_name",
            "assigned_counselor_name",
        ]

    def validate(self, attrs):
        agency = attrs.get("agency", getattr(self.instance, "agency", None))
        _ensure_agency_in_tenant_business(self, agency)
        return attrs


class StudentFileAttachmentPayloadSerializer(serializers.Serializer):
    """
    Writable payload for student-file attachments.
    """

    id = serializers.IntegerField(required=False)
    title = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    verification_status = serializers.ChoiceField(
        choices=ReviewStatusChoice.choices,
        required=False,
        allow_null=True,
    )
    verification_note = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class AppliedUniversityPayloadSerializer(serializers.Serializer):
    """
    Writable payload for one applied-university row.
    """

    id = serializers.IntegerField(required=False)
    university = serializers.IntegerField(required=False, allow_null=True)
    country = serializers.IntegerField(required=False, allow_null=True)
    intake = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    subject = serializers.IntegerField(required=False, allow_null=True)
    application_status = serializers.ChoiceField(
        choices=ReviewStatusChoice.choices,
        required=False,
        allow_null=True,
    )
    review_note = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class StudentFileSerializer(serializers.ModelSerializer):
    """
    Student file API: includes ``is_own_agency`` (all non soft-delete model fields are exposed via ``exclude``).
    """

    agency_name = serializers.CharField(source="agency.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    agency_details = serializers.SerializerMethodField(read_only=True)
    created_by_details = serializers.SerializerMethodField(read_only=True)
    attachments = StudentFileAttachmentPayloadSerializer(many=True, write_only=True, required=False)
    attachment_details = serializers.SerializerMethodField(read_only=True)
    applied_universities = AppliedUniversityPayloadSerializer(many=True, required=False, write_only=True)
    applied_university_details = serializers.SerializerMethodField(read_only=True)
    workflow_steps = serializers.SerializerMethodField(read_only=True)
    generated_student_credentials = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StudentFile
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = [
            "student_file_id",
            "slug",
            "created_at",
            "updated_at",
            "created_by",
            "agency_name",
            "created_by_name",
            "agency_details",
            "created_by_details",
            "attachment_details",
            "applied_university_details",
            "workflow_steps",
            "generated_student_credentials",
            "website_submission_uuid",
        ]

    def get_agency_details(self, obj):
        if not obj.agency:
            return None
        return {
            "id": obj.agency.id,
            "name": obj.agency.name,
            "slug": obj.agency.slug,
            "status": obj.agency.status,
        }

    def get_created_by_details(self, obj):
        if not obj.created_by:
            return None
        return {
            "id": obj.created_by.id,
            "name": getattr(obj.created_by, "name", None),
            "email": getattr(obj.created_by, "email", None),
        }

    def get_attachment_details(self, obj):
        return [
            {
                "id": attachment.id,
                "title": attachment.title,
                "file_url": attachment.file_url,
                "verification_status": attachment.verification_status,
                "verification_note": attachment.verification_note,
                "verified_at": attachment.verified_at,
                "verified_by_name": getattr(attachment.verified_by, "name", None),
                "slug": attachment.slug,
            }
            for attachment in obj.attachments.all()
        ]

    def get_applied_university_details(self, obj):
        raw_rows = obj.applied_universities.values(
            "id",
            "university_id",
            "university__university_name",
            "country_id",
            "country__name",
            "intake",
            "subject_id",
            "subject__subject_name",
            "subject__program_id",
            "subject__program__program_id",
            "subject__program__program__name",
            "subject__program__university_id",
            "subject__program__university__university_name",
            "application_status",
            "review_note",
            "reviewed_at",
            "slug",
        )
        return [
            {
                "id": row["id"],
                "university": row["university_id"],
                "university_name": row["university__university_name"],
                "country": row["country_id"],
                "country_name": row["country__name"],
                "intake": row["intake"],
                "subject": row["subject_id"],
                "subject_name": row["subject__subject_name"],
                "program": row["subject__program_id"],
                "program_master": row["subject__program__program_id"],
                "program_name": row["subject__program__program__name"],
                "program_university": row["subject__program__university_id"],
                "program_university_name": row["subject__program__university__university_name"],
                "application_status": row["application_status"],
                "review_note": row["review_note"],
                "reviewed_at": row["reviewed_at"],
                "slug": row["slug"],
            }
            for row in raw_rows
        ]

    def get_workflow_steps(self, obj):
        attachment_rows = list(obj.attachments.values("verification_status"))
        applied_rows = list(obj.applied_universities.values("application_status"))
        student_account = getattr(obj, "portal_user", None)

        def _status_counter(rows, field_name):
            counts = {
                ReviewStatusChoice.PENDING: 0,
                ReviewStatusChoice.APPROVED: 0,
                ReviewStatusChoice.REJECTED: 0,
            }
            for row in rows:
                raw_status = row.get(field_name) or ReviewStatusChoice.PENDING
                if raw_status not in counts:
                    counts[ReviewStatusChoice.PENDING] += 1
                else:
                    counts[raw_status] += 1
            return counts

        document_counts = _status_counter(attachment_rows, "verification_status")
        application_counts = _status_counter(applied_rows, "application_status")
        return {
            "student_account": {
                "is_created": bool(student_account),
                "login_student_id": getattr(student_account, "user_id", None) if student_account else None,
                "is_verified": bool(getattr(student_account, "is_verified", False)) if student_account else False,
            },
            "profile": {
                "status": obj.current_status,
            },
            "documents": {
                "total": len(attachment_rows),
                "pending": document_counts[ReviewStatusChoice.PENDING],
                "approved": document_counts[ReviewStatusChoice.APPROVED],
                "rejected": document_counts[ReviewStatusChoice.REJECTED],
            },
            "university_applications": {
                "total": len(applied_rows),
                "pending": application_counts[ReviewStatusChoice.PENDING],
                "approved": application_counts[ReviewStatusChoice.APPROVED],
                "rejected": application_counts[ReviewStatusChoice.REJECTED],
            },
        }

    def get_generated_student_credentials(self, obj):
        request = self.context.get("request")
        if request and is_student_portal_user(getattr(request, "user", None)):
            return None
        student_login_id = getattr(obj, "_generated_student_login_id", None)
        delivery_channel = getattr(obj, "_generated_student_credentials_channel", None)
        email_sent_successfully = getattr(obj, "_generated_student_credentials_email_sent", None)
        email_delivery_message = getattr(obj, "_generated_student_credentials_email_message", None)
        recipient_email = getattr(obj, "_generated_student_credentials_recipient", None)
        if not student_login_id:
            return None
        return {
            "student_id": student_login_id,
            "delivery_channel": delivery_channel,
            "email_sent": email_sent_successfully,
            "email_delivery_message": email_delivery_message,
            "recipient_email": recipient_email,
        }

    def validate(self, attrs):
        request = self.context.get("request")
        request_user = getattr(request, "user", None) if request else None
        if request_user and is_student_portal_user(request_user) and self.instance is not None:
            allowed_fields = {"attachments", "applied_universities"}
            incoming_fields = set(self.initial_data.keys())
            disallowed_fields = sorted(incoming_fields - allowed_fields)
            if disallowed_fields:
                raise serializers.ValidationError(
                    {
                        "detail": (
                            "Students may only update document uploads and university-application requests. "
                            f"Unsupported fields: {', '.join(disallowed_fields)}"
                        )
                    }
                )
        return attrs

    def _build_student_portal_identity(self, student_file):
        student_login_id = (student_file.student_file_id or "").strip()
        if not student_login_id:
            raise serializers.ValidationError({"student_file_id": "Student file id is required to build student login."})
        preferred_student_email = (student_file.email or "").strip().lower()
        synthetic_student_email = f"{student_login_id.lower()}@student.portal.local"
        selected_login_email = synthetic_student_email
        if preferred_student_email:
            email_already_used = User.objects.filter(email__iexact=preferred_student_email).exists()
            if not email_already_used:
                selected_login_email = preferred_student_email
        return student_login_id, selected_login_email

    def _create_or_sync_student_portal_user(self, student_file):
        student_login_id, selected_login_email = self._build_student_portal_identity(student_file)
        existing_portal_user = User.objects.filter(linked_student_file=student_file).first()
        if existing_portal_user:
            fields_to_update = []
            if existing_portal_user.user_id != student_login_id:
                existing_portal_user.user_id = student_login_id
                fields_to_update.append("user_id")
            if existing_portal_user.email != selected_login_email:
                existing_portal_user.email = selected_login_email
                fields_to_update.append("email")
            if existing_portal_user.parent_business_id != student_file.business_id:
                existing_portal_user.parent_business_id = student_file.business_id
                fields_to_update.append("parent_business")
            if existing_portal_user.parent_agency_id != student_file.agency_id:
                existing_portal_user.parent_agency_id = student_file.agency_id
                fields_to_update.append("parent_agency")
            if existing_portal_user.user_type != auth_constants.UserTypeChoice.STUDENT:
                existing_portal_user.user_type = auth_constants.UserTypeChoice.STUDENT
                fields_to_update.append("user_type")
            if not existing_portal_user.is_active:
                existing_portal_user.is_active = True
                fields_to_update.append("is_active")
            if fields_to_update:
                existing_portal_user.save(update_fields=fields_to_update + ["updated_at"])
            return existing_portal_user

        temporary_password = get_random_string(10)
        student_user = User(
            name=f"{student_file.given_name} {student_file.surname}".strip(),
            user_id=student_login_id,
            email=selected_login_email,
            phone=student_file.phone_whatsapp,
            user_type=auth_constants.UserTypeChoice.STUDENT,
            parent_agency=student_file.agency,
            parent_business=student_file.business,
            linked_student_file=student_file,
            is_active=True,
        )
        student_user.set_password(temporary_password)
        student_user.save()
        student_file._generated_student_login_id = student_login_id
        student_file._generated_student_credentials_channel = "EMAIL"
        student_file._generated_student_credentials_recipient = student_file.email
        email_sent_successfully, provider_response_message = email_utils.send_student_portal_credentials_email(
            recipient_email=student_file.email,
            student_login_id=student_login_id,
            temporary_password=temporary_password,
            student_name=student_user.name,
            student_file_id=student_file.student_file_id,
            agency_name=student_file.agency.name if student_file.agency else None,
            include_credentials=True,
        )
        student_file._generated_student_credentials_email_sent = email_sent_successfully
        student_file._generated_student_credentials_email_message = provider_response_message
        return student_user

    def _tenant_scoped_queryset(self, queryset):
        """
        Prevent cross-tenant FK picks: tenants may reference rows within their ``business`` slice.
        """
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if not user or not user.is_authenticated or user_is_master_admin(user):
            return queryset
        business_pk = tenant_business_id(user)
        if business_pk:
            concrete_names = {f.name for f in queryset.model._meta.fields}
            if "business" in concrete_names:
                return queryset.filter(business_id=business_pk)
            return queryset.none()
        return queryset.none()

    def _resolve_subject(self, subject_id=None):
        if subject_id is not None:
            try:
                return self._tenant_scoped_queryset(UniversityProgramSubject.objects.all()).get(id=subject_id)
            except UniversityProgramSubject.DoesNotExist:
                raise serializers.ValidationError({"subject": f"Subject id {subject_id} does not exist."})
        return None

    def _resolve_university_and_country(self, university_id=None, country_id=None):
        university_obj = None
        country_obj = None

        if university_id is not None:
            try:
                university_obj = self._tenant_scoped_queryset(
                    University.objects.select_related("country")
                ).get(id=university_id)
            except University.DoesNotExist:
                raise serializers.ValidationError({"university": f"University id {university_id} does not exist."})
            country_obj = university_obj.country
            if isinstance(country_obj, University):
                raise serializers.ValidationError(
                    {"university": "Selected university has invalid country relation. Please contact support."}
                )

        if country_id is not None:
            try:
                requested_country = self._tenant_scoped_queryset(Country.objects.all()).get(id=country_id)
            except Country.DoesNotExist:
                raise serializers.ValidationError({"country": f"Country id {country_id} does not exist."})
            if university_obj and requested_country.id != university_obj.country_id:
                raise serializers.ValidationError(
                    {"country": "Selected country does not match the selected university country."}
                )
            country_obj = requested_country

        return university_obj, country_obj

    def _upsert_attachments(self, student_file, attachments_data, *, replace_links=True):
        request = self.context.get("request")
        request_user = getattr(request, "user", None) if request else None
        is_student_user = bool(request_user and is_student_portal_user(request_user))
        student_attachment_ids = set(student_file.attachments.values_list("id", flat=True))
        attachment_ids = []
        for row in attachments_data:
            attachment_id = row.get("id")
            title = row.get("title")
            file_url = row.get("file_url")
            requested_status = row.get("verification_status")
            requested_note = row.get("verification_note")
            if attachment_id:
                try:
                    attachment_obj = self._tenant_scoped_queryset(StudentFileAttachment.objects.all()).get(
                        id=attachment_id
                    )
                except StudentFileAttachment.DoesNotExist:
                    raise serializers.ValidationError({"attachments": f"Attachment id {attachment_id} does not exist."})
                if is_student_user and attachment_obj.id not in student_attachment_ids:
                    raise serializers.ValidationError(
                        {"attachments": f"Attachment id {attachment_id} is not linked to this student file."}
                    )
                attachment_obj.title = title if title is not None else attachment_obj.title
                attachment_obj.file_url = file_url if file_url is not None else attachment_obj.file_url
                if is_student_user:
                    attachment_obj.verification_status = ReviewStatusChoice.PENDING
                    attachment_obj.verification_note = requested_note or attachment_obj.verification_note
                    attachment_obj.verified_by = None
                    attachment_obj.verified_at = None
                elif requested_status is not None:
                    attachment_obj.verification_status = requested_status
                    attachment_obj.verification_note = requested_note
                    attachment_obj.verified_by = request_user if requested_status != ReviewStatusChoice.PENDING else None
                    attachment_obj.verified_at = timezone.now() if requested_status != ReviewStatusChoice.PENDING else None
                attachment_obj.save()
            else:
                # New attachment: students always start pending; staff uploads default to approved
                # unless they send an explicit ``verification_status`` in the row.
                if is_student_user:
                    create_status = ReviewStatusChoice.PENDING
                elif requested_status is not None:
                    create_status = requested_status
                else:
                    create_status = ReviewStatusChoice.APPROVED
                verified_by_user = (
                    request_user
                    if create_status in (ReviewStatusChoice.APPROVED, ReviewStatusChoice.REJECTED)
                    else None
                )
                verified_at_value = (
                    timezone.now()
                    if create_status in (ReviewStatusChoice.APPROVED, ReviewStatusChoice.REJECTED)
                    else None
                )
                attachment_obj = StudentFileAttachment.objects.create(
                    title=title,
                    file_url=file_url,
                    agency=student_file.agency,
                    business=getattr(student_file, "business", None),
                    verification_status=create_status,
                    verification_note=requested_note,
                    verified_by=verified_by_user,
                    verified_at=verified_at_value,
                )
            attachment_ids.append(attachment_obj.id)
        if replace_links:
            student_file.attachments.set(attachment_ids)
        else:
            student_file.attachments.add(*attachment_ids)

    def _upsert_applied_universities(self, student_file, applied_universities_data, *, replace_links=True):
        request = self.context.get("request")
        request_user = getattr(request, "user", None) if request else None
        is_student_user = bool(request_user and is_student_portal_user(request_user))
        student_applied_university_ids = set(student_file.applied_universities.values_list("id", flat=True))
        applied_university_ids = []
        for row in applied_universities_data:
            applied_university_id = row.get("id")
            university_obj, country_obj = self._resolve_university_and_country(
                university_id=row.get("university"),
                country_id=row.get("country"),
            )
            subject_obj = self._resolve_subject(
                subject_id=row.get("subject"),
            )
            intake = row.get("intake")
            requested_status = row.get("application_status")
            requested_note = row.get("review_note")
            if applied_university_id:
                try:
                    applied_university_obj = self._tenant_scoped_queryset(AppliedUniversity.objects.all()).get(
                        id=applied_university_id
                    )
                except AppliedUniversity.DoesNotExist:
                    raise serializers.ValidationError(
                        {"applied_universities": f"Applied university id {applied_university_id} does not exist."}
                    )
                if is_student_user and applied_university_obj.id not in student_applied_university_ids:
                    raise serializers.ValidationError(
                        {"applied_universities": f"Application id {applied_university_id} is not linked to this student file."}
                    )
                if row.get("university", None) is not None:
                    applied_university_obj.university = university_obj
                if row.get("country", None) is not None:
                    applied_university_obj.country = country_obj
                if intake is not None:
                    applied_university_obj.intake = intake
                applied_university_obj.subject = subject_obj
                if is_student_user:
                    applied_university_obj.application_status = ReviewStatusChoice.PENDING
                    applied_university_obj.review_note = requested_note or applied_university_obj.review_note
                    applied_university_obj.reviewed_by = None
                    applied_university_obj.reviewed_at = None
                elif requested_status is not None:
                    applied_university_obj.application_status = requested_status
                    applied_university_obj.review_note = requested_note
                    applied_university_obj.reviewed_by = request_user if requested_status != ReviewStatusChoice.PENDING else None
                    applied_university_obj.reviewed_at = timezone.now() if requested_status != ReviewStatusChoice.PENDING else None
                applied_university_obj.save()
            else:
                if is_student_user:
                    requested_status = ReviewStatusChoice.PENDING
                applied_university_obj = AppliedUniversity.objects.create(
                    agency=student_file.agency,
                    business=getattr(student_file, "business", None),
                    university=university_obj,
                    country=country_obj,
                    intake=intake,
                    subject=subject_obj,
                    application_status=requested_status or ReviewStatusChoice.PENDING,
                    review_note=requested_note,
                    reviewed_by=(
                        request_user
                        if requested_status in (ReviewStatusChoice.APPROVED, ReviewStatusChoice.REJECTED)
                        else None
                    ),
                    reviewed_at=(
                        timezone.now()
                        if requested_status in (ReviewStatusChoice.APPROVED, ReviewStatusChoice.REJECTED)
                        else None
                    ),
                )
            applied_university_ids.append(applied_university_obj.id)
        if replace_links:
            student_file.applied_universities.set(applied_university_ids)
        else:
            student_file.applied_universities.add(*applied_university_ids)

    @transaction.atomic
    def create(self, validated_data):
        attachments_data = validated_data.pop("attachments", [])
        applied_universities_data = validated_data.pop("applied_universities", [])
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user
        student_file = StudentFile.objects.create(**validated_data)
        if attachments_data:
            self._upsert_attachments(student_file, attachments_data)
        if applied_universities_data:
            self._upsert_applied_universities(student_file, applied_universities_data)
        self._create_or_sync_student_portal_user(student_file)
        return student_file

    @transaction.atomic
    def update(self, instance, validated_data):
        attachments_data = validated_data.pop("attachments", None)
        applied_universities_data = validated_data.pop("applied_universities", None)
        request = self.context.get("request")
        request_user = getattr(request, "user", None) if request else None
        is_student_user = bool(request_user and is_student_portal_user(request_user))
        student_file = super().update(instance, validated_data)
        if attachments_data is not None:
            self._upsert_attachments(student_file, attachments_data, replace_links=not is_student_user)
        if applied_universities_data is not None:
            self._upsert_applied_universities(student_file, applied_universities_data, replace_links=not is_student_user)
        self._create_or_sync_student_portal_user(student_file)
        return student_file


class PublicCountryCatalogSerializer(serializers.ModelSerializer):
    """
    Public website serializer for country cards and country details.
    Includes basic info fields shown in destination quick facts blocks.
    """

    class Meta:
        model = Country
        fields = [
            "id",
            "name",
            "slug",
            "avg_tuition_public",
            "living_cost",
            "language",
            "intake_periods",
            "ielts_required",
            "scholarship",
            "visa_type",
            "work_rights",
        ]


class PublicUniversityCatalogSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = University
        fields = [
            "id",
            "university_name",
            "slug",
            "country",
            "country_name",
            "image_url",
            "minimum_ielts_score",
            "notes",
        ]


class PublicStudentFileCreateSerializer(serializers.Serializer):
    """
    Public website student file payload.
    Creates a student file + optional applied university link and triggers
    student portal credential generation email.
    """

    business = serializers.PrimaryKeyRelatedField(queryset=Business.objects.all(), required=False, allow_null=True)
    business_slug = serializers.CharField(required=False, allow_blank=False)
    given_name = serializers.CharField(max_length=100)
    surname = serializers.CharField(max_length=100)
    middle_name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    passport_number = serializers.CharField(max_length=100)
    phone_whatsapp = serializers.CharField(max_length=30)
    email = serializers.EmailField()
    date_of_birth = serializers.DateField()
    father_name = serializers.CharField(max_length=150)
    mother_name = serializers.CharField(max_length=150)
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all(), required=False, allow_null=True)
    university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all(), required=False, allow_null=True)
    intake = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    subject = serializers.PrimaryKeyRelatedField(
        queryset=UniversityProgramSubject.objects.all(),
        required=False,
        allow_null=True,
    )
    message = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    gender = serializers.ChoiceField(choices=GenderChoice.choices, required=False, default=GenderChoice.OTHER)
    nationality = serializers.CharField(max_length=100, required=False, allow_blank=True)
    place_of_birth = serializers.CharField(max_length=150, required=False, allow_blank=True)
    present_address = serializers.CharField(required=False, allow_blank=True)
    permanent_address = serializers.CharField(required=False, allow_blank=True)
    passport_photo_url = serializers.URLField(max_length=1000, required=False, allow_blank=True, allow_null=True)
    education_background = serializers.JSONField(required=False, allow_null=True)
    family_particulars = serializers.JSONField(required=False, allow_null=True)
    translator_profile = serializers.JSONField(required=False, allow_null=True)
    translated_documents_note = serializers.CharField(max_length=500, required=False, allow_blank=True)
    application_statement = serializers.CharField(required=False, allow_blank=True)
    highest_education_postal_code = serializers.CharField(max_length=30, required=False, allow_blank=True)
    highest_education_address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    highest_education_fax = serializers.CharField(max_length=80, required=False, allow_blank=True)
    highest_education_website = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate(self, attrs):
        selected_business = attrs.get("business")
        selected_business_slug = (attrs.get("business_slug") or "").strip()
        if not selected_business and not selected_business_slug:
            raise serializers.ValidationError({"business": "Provide either business id or business_slug."})
        if not selected_business and selected_business_slug:
            selected_business = Business.objects.filter(slug=selected_business_slug, is_active=True).first()
            if not selected_business:
                raise serializers.ValidationError({"business_slug": "Business not found."})
            attrs["business"] = selected_business

        selected_country = attrs.get("country")
        selected_university = attrs.get("university")
        selected_subject = attrs.get("subject")

        if selected_country and selected_country.business_id != selected_business.id:
            raise serializers.ValidationError({"country": "Selected country does not belong to the selected business."})
        if selected_university and selected_university.business_id != selected_business.id:
            raise serializers.ValidationError(
                {"university": "Selected university does not belong to the selected business."}
            )
        if selected_country and selected_university and selected_university.country_id != selected_country.id:
            raise serializers.ValidationError({"university": "University must belong to the selected country."})
        if selected_subject and selected_university and selected_subject.program.university_id != selected_university.id:
            raise serializers.ValidationError({"subject": "Subject must belong to the selected university."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("business_slug", None)
        selected_country = validated_data.pop("country", None)
        selected_university = validated_data.pop("university", None)
        selected_intake = validated_data.pop("intake", None)
        selected_subject = validated_data.pop("subject", None)
        message = validated_data.pop("message", None)
        selected_business = validated_data["business"]

        student_file = StudentFile.objects.create(
            agency=None,
            business=selected_business,
            is_website_submission=True,
            notes=message,
            **validated_data,
        )

        if selected_university or selected_country or selected_subject or selected_intake:
            applied_university = AppliedUniversity.objects.create(
                agency=None,
                business=selected_business,
                university=selected_university,
                country=selected_country,
                intake=selected_intake,
                subject=selected_subject,
                application_status=ReviewStatusChoice.PENDING,
            )
            student_file.applied_universities.add(applied_university)

        # Reuse the same logic as internal student-file creation:
        # create portal user and queue login credentials email to the student.
        internal_student_serializer = StudentFileSerializer(context=self.context)
        internal_student_serializer._create_or_sync_student_portal_user(student_file)
        return student_file

class UniversityIntakeSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source="university.country.name", read_only=True)

    class Meta:
        model = UniversityIntake
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at", "country_name"]


class UniversityProgramSubjectSerializer(serializers.ModelSerializer):
    """
    Subject + track under a program (API uses ``subject_name`` / ``track_name``).
    ``is_active`` is omitted; new rows use the model default (True).
    """

    class Meta:
        model = UniversityProgramSubject
        exclude = ["deleted_at", "deleted_by", "is_deleted", "program", "is_active"]
        read_only_fields = ["slug", "created_at", "updated_at"]


class UniversityProgramSerializer(serializers.ModelSerializer):
    subjects = UniversityProgramSubjectSerializer(many=True, read_only=True)
    country_name = serializers.CharField(source="university.country.name", read_only=True)
    program_name = serializers.CharField(source="program.name", read_only=True)

    class Meta:
        model = UniversityProgram
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at", "country_name", "program_name"]


class UniversityIntakeNestedSerializer(serializers.ModelSerializer):
    """Nested under university create/update (intake rows from the form)."""

    class Meta:
        model = UniversityIntake
        exclude = ["deleted_at", "deleted_by", "is_deleted", "university"]
        read_only_fields = ["slug", "created_at", "updated_at"]


class UniversityProgramNestedSerializer(serializers.ModelSerializer):
    """One program checkbox plus its subject/track rows."""

    subjects = UniversityProgramSubjectSerializer(many=True, required=False)
    program_name = serializers.CharField(source="program.name", read_only=True)

    class Meta:
        model = UniversityProgram
        exclude = ["deleted_at", "deleted_by", "is_deleted", "university"]
        read_only_fields = ["slug", "created_at", "updated_at", "program_name"]


class UniversitySerializer(serializers.ModelSerializer):
    intakes = UniversityIntakeNestedSerializer(many=True, required=False)
    programs = UniversityProgramNestedSerializer(many=True, required=False)
    country_name = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = University
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at", "country_name"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        agency = attrs.get("agency", getattr(self.instance, "agency", None))
        country = attrs.get("country", getattr(self.instance, "country", None))
   
        business = attrs.get("business", getattr(self.instance, "business", None))
    
   
        return attrs

    def validate_intakes(self, intakes):
        names = [item.get("intake_name", "").strip() for item in intakes]
        if any(not name for name in names):
            raise serializers.ValidationError("Each intake must have a non-empty name.")
        return intakes

    def validate_programs(self, programs):
        return programs

    @transaction.atomic
    def create(self, validated_data):
        intakes_data = validated_data.pop("intakes", [])
        programs_data = validated_data.pop("programs", [])
        university = University.objects.create(**validated_data)
        for intake_row in intakes_data:
            UniversityIntake.objects.create(university=university, **intake_row)
        for program_row in programs_data:
            subjects_data = program_row.pop("subjects", [])
            program_fk = program_row.get("program")
            program_id = program_fk.id if hasattr(program_fk, "id") else program_fk
            program_master = Program.objects.get(pk=program_id)
     

            program_obj = UniversityProgram.objects.create(university=university, **program_row)
            for subject_row in subjects_data:
                UniversityProgramSubject.objects.create(program=program_obj, **subject_row)
        return university

    @transaction.atomic
    def update(self, instance, validated_data):
        intakes_data = validated_data.pop("intakes", None)
        programs_data = validated_data.pop("programs", None)
        university = super().update(instance, validated_data)
        if intakes_data is not None:
            university.intakes.all().delete()
            for intake_row in intakes_data:
                UniversityIntake.objects.create(university=university, **intake_row)
        if programs_data is not None:
            university.programs.all().delete()
            for program_row in programs_data:
                subjects_data = program_row.pop("subjects", [])
                program_fk = program_row.get("program")
                program_id = program_fk.id if hasattr(program_fk, "id") else program_fk
                program_master = Program.objects.get(pk=program_id)

         
                program_obj = UniversityProgram.objects.create(university=university, **program_row)
                for subject_row in subjects_data:
                    UniversityProgramSubject.objects.create(program=program_obj, **subject_row)
        return university


class OfficeCostSerializer(serializers.ModelSerializer):
    agency_name = serializers.CharField(source="agency.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = OfficeCost
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at", "created_by", "agency_name", "created_by_name"]

    def validate(self, attrs):
        agency = attrs.get("agency", getattr(self.instance, "agency", None))
        _ensure_agency_in_tenant_business(self, agency)
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class StudentCostSerializer(serializers.ModelSerializer):
    agency_name = serializers.CharField(source="agency.name", read_only=True)
    student_file_name = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = StudentCost
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = [
            "slug",
            "created_at",
            "updated_at",
            "created_by",
            "agency_name",
            "student_file_name",
            "created_by_name",
        ]

    def get_student_file_name(self, obj):
        sf = obj.student_file
        return f"{sf.given_name} {sf.surname}".strip()

    def validate(self, attrs):
        student_file = attrs.get("student_file", getattr(self.instance, "student_file", None))
        agency = attrs.get("agency", getattr(self.instance, "agency", None))
        if student_file and agency and student_file.agency_id and student_file.agency_id != agency.id:
            raise serializers.ValidationError("Selected student file does not belong to the provided agency.")
        _ensure_agency_in_tenant_business(self, agency)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated and not user_is_master_admin(user):
            tenant_bid = tenant_business_id(user)
            if tenant_bid and student_file:
                sf_bid = getattr(student_file, "business_id", None) or _agency_business_pk(
                    getattr(student_file, "agency_id", None)
                )
                if sf_bid and sf_bid != tenant_bid:
                    raise serializers.ValidationError({"student_file": "Student file must belong to your business."})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user
        return super().create(validated_data)


# --- OpenAPI / drf-spectacular only (document ``application-progress`` custom action) ---


class ApplicationProgressStepSchemaSerializer(serializers.Serializer):
    """One row in ``GET …/application-progress/`` → ``steps``."""

    key = serializers.CharField(
        help_text="Stable step id (same keys as PATCH). Valid keys: " + ", ".join(STEP_KEYS) + "."
    )
    label = serializers.CharField(help_text="Human-readable label for UI.")
    order = serializers.IntegerField(help_text="1-based order in the pipeline.")
    state = serializers.ChoiceField(
        choices=["upcoming", "in_progress", "completed"],
        help_text="Gated timeline state for this step.",
    )
    manual = serializers.BooleanField(
        help_text="If true, this step was **locked** by staff; auto-sync will not overwrite it."
    )


class ApplicationProgressGetSchemaSerializer(serializers.Serializer):
    """Response shape for ``GET /student-files/{slug}/application-progress/``."""

    student_file_id = serializers.CharField(allow_null=True, required=False)
    slug = serializers.CharField(help_text="Student file slug (same as detail URL).")
    current_status = serializers.CharField(
        help_text="Coarse ``StudentFile.current_status`` (e.g. FILE_RECEIVED, IN_PROGRESS, FILE_OPENED)."
    )
    current_status_label = serializers.CharField()
    steps = ApplicationProgressStepSchemaSerializer(many=True)


_PATCH_STEP_HELP = (
    "Either a **state string** (`upcoming` | `in_progress` | `completed`) — locks the step for auto-sync — "
    'or an object `{"state": "completed", "manual": true}` (`manual` defaults to true for string form).'
)


class ApplicationProgressPatchSchemaSerializer(serializers.Serializer):
    """
    **PATCH** body for ``/student-files/{slug}/application-progress/`` (staff only).

    Include only keys you want to change. Each key must be one of the ``steps[].key`` values from GET.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for step_key in STEP_KEYS:
            self.fields[step_key] = serializers.JSONField(required=False, help_text=_PATCH_STEP_HELP)
