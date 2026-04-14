from authentication.base import BaseModelViewSet
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated

from ...models import Agency, Customer, OfficeCost, StudentCost, University, UniversityIntake, UniversityProgram
from .serializers import (
    AgencySerializer,
    CustomerSerializer,
    OfficeCostSerializer,
    StudentCostSerializer,
    UniversityIntakeSerializer,
    UniversityProgramSerializer,
    UniversitySerializer,
)


class AgencyViewSet(BaseModelViewSet):
    queryset = Agency.objects.select_related("created_by").all()
    serializer_class = AgencySerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "is_active", "owner_name"]
    search_fields = ["name", "owner_name", "business_email", "phone", "address"]
    ordering_fields = ["created_at", "updated_at", "name", "status"]


class CustomerViewSet(BaseModelViewSet):
    queryset = Customer.objects.select_related("agency", "assigned_counselor").all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["agency", "current_status", "file_from", "assigned_counselor", "gender", "is_active"]
    search_fields = ["customer_id", "passport_number", "given_name", "surname", "email", "phone_whatsapp"]
    ordering_fields = ["created_at", "updated_at", "given_name", "current_status"]


class UniversityViewSet(BaseModelViewSet):
    queryset = University.objects.all()
    serializer_class = UniversitySerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["country", "is_active"]
    search_fields = ["name", "country"]
    ordering_fields = ["created_at", "updated_at", "name", "country"]


class UniversityIntakeViewSet(BaseModelViewSet):
    queryset = UniversityIntake.objects.select_related("university").all()
    serializer_class = UniversityIntakeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["university", "intake_name", "is_active"]
    search_fields = ["intake_name", "university__name", "university__country"]
    ordering_fields = ["created_at", "updated_at", "intake_name"]


class UniversityProgramViewSet(BaseModelViewSet):
    queryset = UniversityProgram.objects.select_related("university").all()
    serializer_class = UniversityProgramSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["university", "program", "is_active"]
    search_fields = ["program", "university__name", "university__country"]
    ordering_fields = ["created_at", "updated_at", "program"]


class OfficeCostViewSet(BaseModelViewSet):
    queryset = OfficeCost.objects.select_related("agency", "created_by").all()
    serializer_class = OfficeCostSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["agency", "created_by", "is_active"]
    search_fields = ["title", "description", "agency__name"]
    ordering_fields = ["created_at", "updated_at", "amount", "title"]


class StudentCostViewSet(BaseModelViewSet):
    queryset = StudentCost.objects.select_related("agency", "customer", "created_by").all()
    serializer_class = StudentCostSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["agency", "customer", "created_by", "is_active"]
    search_fields = ["title", "description", "customer__given_name", "customer__surname", "customer__customer_id"]
    ordering_fields = ["created_at", "updated_at", "amount", "title"]
