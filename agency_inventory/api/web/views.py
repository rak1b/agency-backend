from authentication.base import BaseModelViewSet
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch

from ...models import (
    Agency,
    Customer,
    OfficeCost,
    StudentCost,
    StudentFile,
    University,
    UniversityIntake,
    UniversityProgram,
    UniversityProgramSubject,
)
from .serializers import (
    AgencySerializer,
    CustomerSerializer,
    OfficeCostSerializer,
    StudentCostSerializer,
    StudentFileSerializer,
    UniversityIntakeSerializer,
    UniversityProgramSerializer,
    UniversitySerializer,
)


class AgencyViewSet(BaseModelViewSet):
    queryset = Agency.objects.select_related("created_by").all()
    serializer_class = AgencySerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "is_active", "owner_name"]
    search_fields = ["name", "owner_name", "business_email", "phone", "address"]
    ordering_fields = ["created_at", "updated_at", "name", "status"]


class CustomerViewSet(BaseModelViewSet):
    queryset = Customer.objects.select_related("agency", "assigned_counselor").all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["agency", "current_status", "file_from", "assigned_counselor", "gender", "is_active"]
    search_fields = ["customer_id", "passport_number", "given_name", "surname", "email", "phone_whatsapp"]
    ordering_fields = ["created_at", "updated_at", "given_name", "current_status"]


class StudentFileViewSet(BaseModelViewSet):
    queryset = StudentFile.objects.select_related("agency", "created_by").prefetch_related(
        "attachments",
        "applied_universities",
    ).all()
    serializer_class = StudentFileSerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["agency", "current_status", "file_from", "created_by", "is_active"]
    search_fields = ["student_file_id", "passport_number", "given_name", "surname", "email", "phone_whatsapp"]
    ordering_fields = ["created_at", "updated_at", "given_name", "current_status"]


class UniversityViewSet(BaseModelViewSet):
    queryset = University.objects.select_related("country").prefetch_related(
        Prefetch("intakes", queryset=UniversityIntake.objects.order_by("id")),
        Prefetch(
            "programs",
            queryset=UniversityProgram.objects.prefetch_related(
                Prefetch("subjects", queryset=UniversityProgramSubject.objects.order_by("id"))
            ).order_by("id"),
        ),
    ).all()
    serializer_class = UniversitySerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["country", "is_active"]
    search_fields = ["university_name", "country__name"]
    ordering_fields = ["created_at", "updated_at", "university_name", "country__name"]


class UniversityIntakeViewSet(BaseModelViewSet):
    queryset = UniversityIntake.objects.select_related("university", "university__country").all()
    serializer_class = UniversityIntakeSerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["university", "intake_name", "is_active"]
    search_fields = ["intake_name", "university__university_name", "university__country__name"]
    ordering_fields = ["created_at", "updated_at", "intake_name"]


class UniversityProgramViewSet(BaseModelViewSet):
    queryset = UniversityProgram.objects.select_related("university", "university__country").prefetch_related(
        Prefetch("subjects", queryset=UniversityProgramSubject.objects.order_by("id"))
    )
    serializer_class = UniversityProgramSerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["university", "program", "is_active"]
    search_fields = ["program", "university__university_name", "university__country__name"]
    ordering_fields = ["created_at", "updated_at", "program"]


class OfficeCostViewSet(BaseModelViewSet):
    queryset = OfficeCost.objects.select_related("agency", "created_by").all()
    serializer_class = OfficeCostSerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["agency", "created_by", "is_active"]
    search_fields = ["title", "description", "agency__name"]
    ordering_fields = ["created_at", "updated_at", "amount", "title"]


class StudentCostViewSet(BaseModelViewSet):
    queryset = StudentCost.objects.select_related("agency", "student_file", "created_by").all()
    serializer_class = StudentCostSerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["agency", "student_file", "created_by", "is_active"]
    search_fields = [
        "title",
        "description",
        "student_file__given_name",
        "student_file__surname",
        "student_file__student_file_id",
    ]
    ordering_fields = ["created_at", "updated_at", "amount", "title"]
