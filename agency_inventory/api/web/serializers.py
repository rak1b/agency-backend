from rest_framework import serializers

from django.db import transaction

from ...constants import normalize_university_program_input
from ...models import (
    Agency,
    Customer,
    OfficeCost,
    StudentFile,
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


class StudentFileSerializer(serializers.ModelSerializer):
    """
    Student file API: includes ``is_own_agency`` (all non soft-delete model fields are exposed via ``exclude``).
    """

    agency_name = serializers.CharField(source="agency.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)

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
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class UniversityIntakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityIntake
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at"]


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

    class Meta:
        model = UniversityProgram
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at"]

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

    class Meta:
        model = University
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at"]

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
