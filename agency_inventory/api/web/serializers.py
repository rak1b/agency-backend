from rest_framework import serializers

from ...models import (
    Agency,
    Customer,
    OfficeCost,
    StudentFile,
    StudentCost,
    University,
    UniversityIntake,
    UniversityProgram,
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


class UniversityProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityProgram
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at"]


class UniversitySerializer(serializers.ModelSerializer):
    intakes = UniversityIntakeSerializer(many=True, read_only=True)
    programs = UniversityProgramSerializer(many=True, read_only=True)

    class Meta:
        model = University
        exclude = ["deleted_at", "deleted_by", "is_deleted"]
        read_only_fields = ["slug", "created_at", "updated_at", "intakes", "programs"]


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
    customer_name = serializers.SerializerMethodField()
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
            "customer_name",
            "created_by_name",
        ]

    def get_customer_name(self, obj):
        return f"{obj.customer.given_name} {obj.customer.surname}".strip()

    def validate(self, attrs):
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        agency = attrs.get("agency", getattr(self.instance, "agency", None))
        if customer and agency and customer.agency_id != agency.id:
            raise serializers.ValidationError("Selected customer does not belong to the provided agency.")
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user
        return super().create(validated_data)
