from rest_framework import serializers

from django.db import transaction

from ...constants import normalize_university_program_input
from ...models import (
    Agency,
    AppliedUniversity,
    Country,
    Customer,
    OfficeCost,
    StudentFile,
    StudentFileAttachment,
    StudentCost,
    University,
    UniversityIntake,
    UniversityProgram,
    UniversityProgramSubject,
)


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


class StudentFileAttachmentPayloadSerializer(serializers.Serializer):
    """
    Writable payload for student-file attachments.
    """

    id = serializers.IntegerField(required=False)
    title = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)


class AppliedUniversityPayloadSerializer(serializers.Serializer):
    """
    Writable payload for one applied-university row.
    """

    id = serializers.IntegerField(required=False)
    university = serializers.IntegerField(required=False, allow_null=True)
    country = serializers.IntegerField(required=False, allow_null=True)
    intake = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    subject = serializers.IntegerField(required=False, allow_null=True)


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
            "subject__program__program",
            "subject__program__university_id",
            "subject__program__university__university_name",
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
                "program_name": row["subject__program__program"],
                "program_university": row["subject__program__university_id"],
                "program_university_name": row["subject__program__university__university_name"],
                "slug": row["slug"],
            }
            for row in raw_rows
        ]

    def _resolve_subject(self, subject_id=None):
        if subject_id is not None:
            try:
                return UniversityProgramSubject.objects.get(id=subject_id)
            except UniversityProgramSubject.DoesNotExist:
                raise serializers.ValidationError({"subject": f"Subject id {subject_id} does not exist."})
        return None

    def _resolve_university_and_country(self, university_id=None, country_id=None):
        university_obj = None
        country_obj = None

        if university_id is not None:
            try:
                university_obj = University.objects.select_related("country").get(id=university_id)
            except University.DoesNotExist:
                raise serializers.ValidationError({"university": f"University id {university_id} does not exist."})
            country_obj = university_obj.country
            if isinstance(country_obj, University):
                raise serializers.ValidationError(
                    {"university": "Selected university has invalid country relation. Please contact support."}
                )

        if country_id is not None:
            try:
                requested_country = Country.objects.get(id=country_id)
            except Country.DoesNotExist:
                raise serializers.ValidationError({"country": f"Country id {country_id} does not exist."})
            if university_obj and requested_country.id != university_obj.country_id:
                raise serializers.ValidationError(
                    {"country": "Selected country does not match the selected university country."}
                )
            country_obj = requested_country

        return university_obj, country_obj

    def _upsert_attachments(self, student_file, attachments_data):
        attachment_ids = []
        for row in attachments_data:
            attachment_id = row.get("id")
            title = row.get("title")
            file_url = row.get("file_url")
            if attachment_id:
                try:
                    attachment_obj = StudentFileAttachment.objects.get(id=attachment_id)
                except StudentFileAttachment.DoesNotExist:
                    raise serializers.ValidationError({"attachments": f"Attachment id {attachment_id} does not exist."})
                attachment_obj.title = title if title is not None else attachment_obj.title
                attachment_obj.file_url = file_url if file_url is not None else attachment_obj.file_url
                attachment_obj.save()
            else:
                attachment_obj = StudentFileAttachment.objects.create(title=title, file_url=file_url)
            attachment_ids.append(attachment_obj.id)
        student_file.attachments.set(attachment_ids)

    def _upsert_applied_universities(self, student_file, applied_universities_data):
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
            if applied_university_id:
                try:
                    applied_university_obj = AppliedUniversity.objects.get(id=applied_university_id)
                except AppliedUniversity.DoesNotExist:
                    raise serializers.ValidationError(
                        {"applied_universities": f"Applied university id {applied_university_id} does not exist."}
                    )
                if row.get("university", None) is not None:
                    applied_university_obj.university = university_obj
                if row.get("country", None) is not None:
                    applied_university_obj.country = country_obj
                if intake is not None:
                    applied_university_obj.intake = intake
                applied_university_obj.subject = subject_obj
                applied_university_obj.save()
            else:
                applied_university_obj = AppliedUniversity.objects.create(
                    university=university_obj,
                    country=country_obj,
                    intake=intake,
                    subject=subject_obj,
                )
            applied_university_ids.append(applied_university_obj.id)
        student_file.applied_universities.set(applied_university_ids)

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
        return student_file

    @transaction.atomic
    def update(self, instance, validated_data):
        attachments_data = validated_data.pop("attachments", None)
        applied_universities_data = validated_data.pop("applied_universities", None)
        student_file = super().update(instance, validated_data)
        if attachments_data is not None:
            self._upsert_attachments(student_file, attachments_data)
        if applied_universities_data is not None:
            self._upsert_applied_universities(student_file, applied_universities_data)
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

    class Meta:
        model = UniversityProgram
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at", "country_name"]

    def validate_program(self, value):
        return normalize_university_program_input(value)


class UniversityIntakeNestedSerializer(serializers.ModelSerializer):
    """Nested under university create/update (intake rows from the form)."""

    class Meta:
        model = UniversityIntake
        exclude = ["deleted_at", "deleted_by", "is_deleted", "university"]
        read_only_fields = ["slug", "created_at", "updated_at"]


class UniversityProgramNestedSerializer(serializers.ModelSerializer):
    """One program checkbox plus its subject/track rows."""

    subjects = UniversityProgramSubjectSerializer(many=True, required=False)

    class Meta:
        model = UniversityProgram
        exclude = ["deleted_at", "deleted_by", "is_deleted", "university"]
        read_only_fields = ["slug", "created_at", "updated_at"]

    def validate_program(self, value):
        return normalize_university_program_input(value)


class UniversitySerializer(serializers.ModelSerializer):
    intakes = UniversityIntakeNestedSerializer(many=True, required=False)
    programs = UniversityProgramNestedSerializer(many=True, required=False)
    country_name = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = University
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at", "country_name"]

    def validate_intakes(self, intakes):
        names = [item.get("intake_name", "").strip() for item in intakes]
        if any(not name for name in names):
            raise serializers.ValidationError("Each intake must have a non-empty name.")
        if len(names) != len(set(names)):
            raise serializers.ValidationError("Intake names must be unique for this university.")
        return intakes

    def validate_programs(self, programs):
        codes = [item.get("program") for item in programs]
        if len(codes) != len(set(codes)):
            raise serializers.ValidationError("Each program type can only appear once per university.")
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
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user
        return super().create(validated_data)
