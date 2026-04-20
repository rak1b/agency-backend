from authentication.base import BaseModelViewSet
from authentication import constants
from authentication.notification_utils import create_notifications_for_event
from datetime import date, timedelta
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Prefetch, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import (
    Agency,
    Country,
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
    CountrySerializer,
    CustomerSerializer,
    InventoryDashboardQuerySerializer,
    OfficeCostSerializer,
    StudentCostSerializer,
    StudentFileSerializer,
    UniversityIntakeSerializer,
    UniversityProgramSerializer,
    UniversitySerializer,
)


class InventoryDashboardAPIView(APIView):
    """
    Dashboard endpoint aligned with the inventory domain instead of the template's ecommerce labels.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        query_serializer = InventoryDashboardQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        validated_filters = query_serializer.validated_data

        agency = validated_filters.get("agency")
        start_date, end_date = self._resolve_date_range(validated_filters)

        agencies_queryset = Agency.objects.all()
        customers_queryset = Customer.objects.filter(created_at__date__range=(start_date, end_date))
        student_files_queryset = StudentFile.objects.filter(created_at__date__range=(start_date, end_date))
        office_costs_queryset = OfficeCost.objects.filter(created_at__date__range=(start_date, end_date))
        student_costs_queryset = StudentCost.objects.filter(created_at__date__range=(start_date, end_date))

        if agency:
            customers_queryset = customers_queryset.filter(agency=agency)
            student_files_queryset = student_files_queryset.filter(agency=agency)
            office_costs_queryset = office_costs_queryset.filter(agency=agency)
            student_costs_queryset = student_costs_queryset.filter(agency=agency)

        month_starts = self._build_month_starts(start_date, end_date)
        monthly_customer_files = self._build_monthly_series(
            queryset=customers_queryset,
            month_starts=month_starts,
            value_field_name="total",
        )
        monthly_office_costs = self._build_monthly_series(
            queryset=office_costs_queryset,
            month_starts=month_starts,
            aggregate_field="amount",
            value_field_name="office_cost",
        )
        monthly_student_costs = self._build_monthly_series(
            queryset=student_costs_queryset,
            month_starts=month_starts,
            aggregate_field="amount",
            value_field_name="student_cost",
        )

        monthly_cost_overview = []
        for month_index, month_start in enumerate(month_starts):
            office_cost_value = monthly_office_costs[month_index]["office_cost"]
            student_cost_value = monthly_student_costs[month_index]["student_cost"]
            monthly_cost_overview.append(
                {
                    "month": month_start.strftime("%b"),
                    "month_key": month_start.strftime("%Y-%m"),
                    "office_cost": office_cost_value,
                    "student_cost": student_cost_value,
                    "total_cost": office_cost_value + student_cost_value,
                }
            )

        current_month_start = self._first_day_of_month(timezone.localdate())
        previous_month_start = self._add_months(current_month_start, -1)
        current_month_end = self._last_day_of_month(current_month_start)
        previous_month_end = self._last_day_of_month(previous_month_start)

        current_month_student_files_count = StudentFile.objects.filter(
            created_at__date__range=(current_month_start, current_month_end),
            **({"agency": agency} if agency else {}),
        ).count()
        previous_month_student_files_count = StudentFile.objects.filter(
            created_at__date__range=(previous_month_start, previous_month_end),
            **({"agency": agency} if agency else {}),
        ).count()

        month_over_month_growth = self._calculate_growth_percentage(
            current_value=current_month_student_files_count,
            previous_value=previous_month_student_files_count,
        )

        country_distribution = self._build_country_distribution(student_files_queryset)
        recent_student_files = self._build_recent_student_files(student_files_queryset)

        response_payload = {
            "filters": {
                "agency": (
                    {
                        "id": agency.id,
                        "name": agency.name,
                        "slug": agency.slug,
                    }
                    if agency
                    else None
                ),
                "start_date": start_date,
                "end_date": end_date,
            },
            "summary": {
                "student_files": {
                    "label": "Student Files",
                    "total": student_files_queryset.count(),
                    "active": student_files_queryset.filter(is_active=True).count(),
                    "current_month": current_month_student_files_count,
                    "previous_month": previous_month_student_files_count,
                    "growth_percentage": month_over_month_growth,
                },
                "agencies": {
                    "label": "Agencies",
                    "total": agencies_queryset.count() if not agency else 1,
                    "active": agencies_queryset.filter(is_active=True).count() if not agency else int(bool(agency.is_active)),
                },
                "customers": {
                    "label": "Customer Files",
                    "total": customers_queryset.count(),
                    "active": customers_queryset.filter(is_active=True).count(),
                },
                "monthly_progress": {
                    "label": "Monthly Progress",
                    "current_month_student_files": current_month_student_files_count,
                    "previous_month_student_files": previous_month_student_files_count,
                    "growth_percentage": month_over_month_growth,
                },
            },
            "charts": {
                "monthly_customer_files": monthly_customer_files,
                "monthly_cost_overview": monthly_cost_overview,
                "country_wise_student_files": country_distribution,
            },
            "recent_student_files": recent_student_files,
        }
        return Response(response_payload)

    def _resolve_date_range(self, validated_filters):
        start_date = validated_filters.get("start_date")
        end_date = validated_filters.get("end_date")

        current_date = timezone.localdate()
        if start_date and not end_date:
            end_date = current_date
        elif end_date and not start_date:
            start_date = self._add_months(self._first_day_of_month(end_date), -11)
        elif not start_date and not end_date:
            end_date = current_date
            current_month_start = self._first_day_of_month(current_date)
            start_date = self._add_months(current_month_start, -11)

        return start_date, end_date

    def _build_monthly_series(self, queryset, month_starts, value_field_name, aggregate_field=None):
        monthly_queryset = queryset.annotate(month=TruncMonth("created_at")).values("month")
        if aggregate_field:
            monthly_queryset = monthly_queryset.annotate(total=Sum(aggregate_field))
        else:
            monthly_queryset = monthly_queryset.annotate(total=Count("id"))

        month_map = {
            row["month"].date().replace(day=1): int(row["total"] or 0)
            for row in monthly_queryset
        }

        return [
            {
                "month": month_start.strftime("%b"),
                "month_key": month_start.strftime("%Y-%m"),
                value_field_name: month_map.get(month_start, 0),
            }
            for month_start in month_starts
        ]

    def _build_country_distribution(self, student_files_queryset):
        student_file_ids = student_files_queryset.values_list("id", flat=True)
        country_rows = list(
            Country.objects.filter(applied_universities__student_files__id__in=student_file_ids)
            .annotate(student_file_count=Count("applied_universities__student_files", distinct=True))
            .values("id", "name", "student_file_count")
            .order_by("-student_file_count", "name")
        )

        distribution_total = sum(row["student_file_count"] for row in country_rows)
        if distribution_total == 0:
            return []

        return [
            {
                "country_id": row["id"],
                "country_name": row["name"],
                "student_file_count": row["student_file_count"],
                "percentage": round((row["student_file_count"] / distribution_total) * 100, 2),
            }
            for row in country_rows
        ]

    def _build_recent_student_files(self, student_files_queryset):
        recent_rows = (
            student_files_queryset.select_related("agency", "created_by")
            .order_by("-created_at")[:5]
        )
        return [
            {
                "id": student_file.id,
                "student_file_id": student_file.student_file_id,
                "slug": student_file.slug,
                "full_name": f"{student_file.given_name} {student_file.surname}".strip(),
                "agency_name": student_file.agency.name if student_file.agency else None,
                "current_status": student_file.current_status,
                "created_at": student_file.created_at,
                "created_by_name": getattr(student_file.created_by, "name", None),
            }
            for student_file in recent_rows
        ]

    def _build_month_starts(self, start_date, end_date):
        month_starts = []
        current_month = self._first_day_of_month(start_date)
        last_month = self._first_day_of_month(end_date)

        while current_month <= last_month:
            month_starts.append(current_month)
            current_month = self._add_months(current_month, 1)

        return month_starts

    def _calculate_growth_percentage(self, current_value, previous_value):
        if previous_value == 0:
            return 100.0 if current_value > 0 else 0.0
        return round(((current_value - previous_value) / previous_value) * 100, 2)

    def _first_day_of_month(self, value):
        return value.replace(day=1)

    def _last_day_of_month(self, value):
        return self._add_months(value, 1) - timedelta(days=1)

    def _add_months(self, value, months):
        month_index = value.month - 1 + months
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        return date(year, month, 1)


class AgencyViewSet(BaseModelViewSet):
    queryset = Agency.objects.select_related("created_by").all()
    serializer_class = AgencySerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "is_active", "owner_name"]
    search_fields = ["name", "owner_name", "business_email", "phone", "address"]
    ordering_fields = ["created_at", "updated_at", "name", "status"]

    def perform_create(self, serializer):
        created_agency = serializer.save()
        create_notifications_for_event(
            entity_type=constants.NotificationEntityTypeChoice.AGENCY,
            action=constants.NotificationActionChoice.CREATED,
            instance=created_agency,
            actor=self.request.user,
        )

    def perform_update(self, serializer):
        updated_agency = serializer.save()
        create_notifications_for_event(
            entity_type=constants.NotificationEntityTypeChoice.AGENCY,
            action=constants.NotificationActionChoice.UPDATED,
            instance=updated_agency,
            actor=self.request.user,
        )


class CountryViewSet(BaseModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "updated_at", "name"]


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

    def perform_create(self, serializer):
        created_student_file = serializer.save()
        create_notifications_for_event(
            entity_type=constants.NotificationEntityTypeChoice.STUDENT_FILE,
            action=constants.NotificationActionChoice.CREATED,
            instance=created_student_file,
            actor=self.request.user,
        )

    def perform_update(self, serializer):
        updated_student_file = serializer.save()
        create_notifications_for_event(
            entity_type=constants.NotificationEntityTypeChoice.STUDENT_FILE,
            action=constants.NotificationActionChoice.UPDATED,
            instance=updated_student_file,
            actor=self.request.user,
        )


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
