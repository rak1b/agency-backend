from authentication.base import BaseModelViewSet, StudentPortalReadOnlyMixin
from authentication import constants
from authentication.tenant_utils import (
    apply_b2b_agency_scope_to_queryset,
    invoice_issuer_agency_stamp_id,
    is_student_portal_user,
    tenant_business_id,
    user_is_b2b_agent_or_employee,
    user_is_master_admin,
)
from authentication.notification_utils import create_notifications_for_event
from datetime import date, timedelta
from rest_framework import filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from django.db.models import Count, Prefetch, Sum
from django.db.models.functions import TruncMonth
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

from ...services.application_progress import (
    apply_admin_progress_patch,
    parse_admin_progress_payload,
    serialize_application_progress,
)
from ...services.hanseo_pdf_context import build_hanseo_template_context, scoped_student_files_queryset

from ...models import (
    Agency,
    Business,
    Country,
    Customer,
    OfficeCost,
    Program,
    StudentCost,
    StudentFile,
    University,
    UniversityIntake,
    UniversityProgram,
    UniversityProgramSubject,
)


class TenantHomeAgencyRowMixin:
    """
    After ``BaseModelViewSet`` business isolation, narrows queryset rows to the user's
    home agency when resolved (mirrors invoices / orders / tickets).
    """

    def _apply_tenant_scope(self, queryset):
        queryset = super()._apply_tenant_scope(queryset)
        return apply_b2b_agency_scope_to_queryset(queryset, getattr(self.request, "user", None))


from .serializers import (
    AgencySerializer,
    ApplicationProgressGetSchemaSerializer,
    ApplicationProgressPatchSchemaSerializer,
    CountrySerializer,
    CustomerSerializer,
    InventoryDashboardQuerySerializer,
    OfficeCostSerializer,
    ProgramSerializer,
    PublicCountryCatalogSerializer,
    PublicStudentFileCreateSerializer,
    PublicUniversityCatalogSerializer,
    StudentCostSerializer,
    StudentFileSerializer,
    UniversityIntakeSerializer,
    UniversityProgramSerializer,
    UniversitySerializer,
)


def inventory_first_day_of_month(value):
    """First calendar day of the month for ``value`` (``date``)."""
    return value.replace(day=1)


def inventory_add_months(value, months):
    """Add ``months`` to ``value`` (``date``), anchored on the first of the month."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def inventory_resolve_dashboard_date_range(validated_filters):
    """
    Same default and partial-date rules as ``InventoryDashboardAPIView._resolve_date_range``.

    Used so student-file list counts align with dashboard ``student_files`` filtering.
    """
    start_date = validated_filters.get("start_date")
    end_date = validated_filters.get("end_date")
    current_date = timezone.localdate()
    if start_date and not end_date:
        end_date = current_date
    elif end_date and not start_date:
        start_date = inventory_add_months(inventory_first_day_of_month(end_date), -11)
    elif not start_date and not end_date:
        end_date = current_date
        current_month_start = inventory_first_day_of_month(current_date)
        start_date = inventory_add_months(current_month_start, -11)
    return start_date, end_date


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
        scoped_business_id = None
        if not user_is_master_admin(request.user):
            scoped_business_id = tenant_business_id(request.user)
            if not scoped_business_id or (agency and getattr(agency, "business_id", None) != scoped_business_id):
                agency = None

        start_date, end_date = self._resolve_date_range(validated_filters)

        agencies_queryset = Agency.objects.all()
        if user_is_master_admin(request.user):
            if agency:
                agencies_queryset = agencies_queryset.filter(pk=agency.pk)
        elif scoped_business_id:
            agencies_queryset = Agency.objects.filter(business_id=scoped_business_id)
            if agency:
                agencies_queryset = agencies_queryset.filter(pk=agency.pk)
        else:
            agencies_queryset = Agency.objects.none()

        customers_queryset = Customer.objects.filter(created_at__date__range=(start_date, end_date))
        student_files_queryset = StudentFile.objects.filter(created_at__date__range=(start_date, end_date))
        office_costs_queryset = OfficeCost.objects.filter(created_at__date__range=(start_date, end_date))
        student_costs_queryset = StudentCost.objects.filter(created_at__date__range=(start_date, end_date))

        if not user_is_master_admin(request.user):
            if scoped_business_id:
                customers_queryset = customers_queryset.filter(business_id=scoped_business_id)
                student_files_queryset = student_files_queryset.filter(business_id=scoped_business_id)
                office_costs_queryset = office_costs_queryset.filter(business_id=scoped_business_id)
                student_costs_queryset = student_costs_queryset.filter(business_id=scoped_business_id)
                if agency:
                    customers_queryset = customers_queryset.filter(agency=agency)
                    student_files_queryset = student_files_queryset.filter(agency=agency)
                    office_costs_queryset = office_costs_queryset.filter(agency=agency)
                    student_costs_queryset = student_costs_queryset.filter(agency=agency)
            else:
                customers_queryset = Customer.objects.none()
                student_files_queryset = StudentFile.objects.none()
                office_costs_queryset = OfficeCost.objects.none()
                student_costs_queryset = StudentCost.objects.none()
        elif agency:
            customers_queryset = customers_queryset.filter(agency=agency)
            student_files_queryset = student_files_queryset.filter(agency=agency)
            office_costs_queryset = office_costs_queryset.filter(agency=agency)
            student_costs_queryset = student_costs_queryset.filter(agency=agency)

        student_portal_linked_id = None
        if is_student_portal_user(request.user):
            student_portal_linked_id = getattr(request.user, "linked_student_file_id", None)
            customers_queryset = customers_queryset.none()
            office_costs_queryset = office_costs_queryset.none()
            if student_portal_linked_id:
                student_files_queryset = student_files_queryset.filter(pk=student_portal_linked_id)
                student_costs_queryset = student_costs_queryset.filter(student_file_id=student_portal_linked_id)
            else:
                student_files_queryset = student_files_queryset.none()
                student_costs_queryset = student_costs_queryset.none()

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

        sf_scope_kwargs = {}
        if agency:
            sf_scope_kwargs["agency"] = agency
        elif scoped_business_id and not user_is_master_admin(request.user):
            sf_scope_kwargs["business_id"] = scoped_business_id

        current_sf_qs = StudentFile.objects.filter(
            created_at__date__range=(current_month_start, current_month_end),
            **sf_scope_kwargs,
        )
        previous_sf_qs = StudentFile.objects.filter(
            created_at__date__range=(previous_month_start, previous_month_end),
            **sf_scope_kwargs,
        )
        if student_portal_linked_id:
            current_sf_qs = current_sf_qs.filter(pk=student_portal_linked_id)
            previous_sf_qs = previous_sf_qs.filter(pk=student_portal_linked_id)
        elif is_student_portal_user(request.user):
            current_sf_qs = current_sf_qs.none()
            previous_sf_qs = previous_sf_qs.none()
        current_month_student_files_count = current_sf_qs.count()
        previous_month_student_files_count = previous_sf_qs.count()

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
        return inventory_resolve_dashboard_date_range(validated_filters)

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
        return inventory_first_day_of_month(value)

    def _last_day_of_month(self, value):
        return inventory_add_months(value, 1) - timedelta(days=1)

    def _add_months(self, value, months):
        return inventory_add_months(value, months)


class PublicCountryCatalogAPIView(APIView):
    """
    Public destination countries list with strict business scoping.
    Optional filters:
    - search=<country name>
    - course=<program id>
    - ielts_score=<float>
    """

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        business_param = (request.query_params.get("business") or "").strip()
        if not business_param:
            return Response({"detail": "Query parameter 'business' is required."}, status=status.HTTP_400_BAD_REQUEST)

        business_queryset = Business.objects.filter(is_active=True)
        if business_param.isdigit():
            business_object = business_queryset.filter(pk=int(business_param)).first()
        else:
            business_object = business_queryset.filter(slug=business_param).first()
        if not business_object:
            return Response({"detail": "Business not found."}, status=status.HTTP_404_NOT_FOUND)

        country_queryset = Country.objects.filter(
            business_id=business_object.id,
            is_active=True,
            universities__is_active=True,
        )

        search_text = (request.query_params.get("search") or "").strip()
        if search_text:
            country_queryset = country_queryset.filter(name__icontains=search_text)

        selected_program = (request.query_params.get("course") or "").strip()
        if selected_program:
            country_queryset = country_queryset.filter(universities__programs__program_id=selected_program)

        requested_ielts_score = (request.query_params.get("ielts_score") or "").strip()
        if requested_ielts_score:
            try:
                requested_ielts_score_value = float(requested_ielts_score)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Invalid ielts_score. Provide a numeric value like 6.5."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            country_queryset = country_queryset.filter(universities__minimum_ielts_score__lte=requested_ielts_score_value)

        serialized_countries = PublicCountryCatalogSerializer(country_queryset.distinct().order_by("name"), many=True)
        return Response(
            {
                "business": {"id": business_object.id, "name": business_object.name, "slug": business_object.slug},
                "count": len(serialized_countries.data),
                "results": serialized_countries.data,
            }
        )


class PublicUniversityCatalogAPIView(APIView):
    """
    Public universities list with country/program/IELTS filters.
    """

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        business_param = (request.query_params.get("business") or "").strip()
        if not business_param:
            return Response({"detail": "Query parameter 'business' is required."}, status=status.HTTP_400_BAD_REQUEST)

        business_queryset = Business.objects.filter(is_active=True)
        if business_param.isdigit():
            business_object = business_queryset.filter(pk=int(business_param)).first()
        else:
            business_object = business_queryset.filter(slug=business_param).first()
        if not business_object:
            return Response({"detail": "Business not found."}, status=status.HTTP_404_NOT_FOUND)

        university_queryset = University.objects.select_related("country").filter(
            business_id=business_object.id,
            is_active=True,
            country__is_active=True,
        )

        selected_country = (request.query_params.get("country") or "").strip()
        if selected_country:
            university_queryset = university_queryset.filter(country_id=selected_country)

        selected_program = (request.query_params.get("course") or "").strip()
        if selected_program:
            university_queryset = university_queryset.filter(programs__program_id=selected_program)

        requested_ielts_score = (request.query_params.get("ielts_score") or "").strip()
        if requested_ielts_score:
            try:
                requested_ielts_score_value = float(requested_ielts_score)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Invalid ielts_score. Provide a numeric value like 6.5."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            university_queryset = university_queryset.filter(minimum_ielts_score__lte=requested_ielts_score_value)

        search_text = (request.query_params.get("search") or "").strip()
        if search_text:
            university_queryset = university_queryset.filter(university_name__icontains=search_text)

        serialized_universities = PublicUniversityCatalogSerializer(
            university_queryset.distinct().order_by("university_name"),
            many=True,
        )
        return Response(
            {
                "business": {"id": business_object.id, "name": business_object.name, "slug": business_object.slug},
                "count": len(serialized_universities.data),
                "results": serialized_universities.data,
            }
        )


class PublicUniversitySelectionAPIView(APIView):
    """
    Public university detail endpoint for varsity selection step.
    """

    permission_classes = [AllowAny]

    def get(self, request, slug, *args, **kwargs):
        business_param = (request.query_params.get("business") or "").strip()
        if not business_param:
            return Response({"detail": "Query parameter 'business' is required."}, status=status.HTTP_400_BAD_REQUEST)

        business_queryset = Business.objects.filter(is_active=True)
        if business_param.isdigit():
            business_object = business_queryset.filter(pk=int(business_param)).first()
        else:
            business_object = business_queryset.filter(slug=business_param).first()
        if not business_object:
            return Response({"detail": "Business not found."}, status=status.HTTP_404_NOT_FOUND)

        selected_university = (
            University.objects.select_related("country")
            .prefetch_related("intakes", "programs__program", "programs__subjects")
            .filter(business_id=business_object.id, slug=slug, is_active=True)
            .first()
        )
        if not selected_university:
            return Response({"detail": "University not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "university": PublicUniversityCatalogSerializer(selected_university).data,
                "country": PublicCountryCatalogSerializer(selected_university.country).data,
                "intakes": [
                    {"id": intake.id, "name": intake.intake_name}
                    for intake in selected_university.intakes.filter(is_active=True).order_by("intake_name")
                ],
                "programs": [
                    {
                        "id": university_program.program_id,
                        "name": university_program.program.name,
                        "subjects": [
                            {"id": subject.id, "subject_name": subject.subject_name, "track_name": subject.track_name}
                            for subject in university_program.subjects.filter(is_active=True).order_by("id")
                        ],
                    }
                    for university_program in selected_university.programs.filter(is_active=True)
                ],
            }
        )


class PublicStudentFileCreateAPIView(APIView):
    """
    Public website endpoint to submit student files.
    Creates student file, links selected university data, and triggers email credentials.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PublicStudentFileCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        created_student_file = serializer.save()
        return Response(
            {
                "detail": "Student file submitted successfully.",
                "student_file_id": created_student_file.student_file_id,
                "website_submission_uuid": created_student_file.website_submission_uuid,
                "student_file_slug": created_student_file.slug,
                "current_status": created_student_file.current_status,
            },
            status=status.HTTP_201_CREATED,
        )


class AgencyViewSet(BaseModelViewSet):
    queryset = Agency.objects.select_related("business", "created_by").all()
    serializer_class = AgencySerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["business", "status", "is_active", "owner_name"]
    search_fields = ["name", "owner_name", "business_email", "phone", "address"]
    ordering_fields = ["created_at", "updated_at", "name", "status"]

    def _apply_tenant_scope(self, queryset):
        """
        ``Agency`` rows carry ``business``, not ``agency``; desk users only see their own
        Agency profile PK (their ``parent_agency``).
        """
        queryset = super()._apply_tenant_scope(queryset)
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated or user_is_master_admin(user):
            return queryset
        if is_student_portal_user(user):
            return queryset
        stamped_agency_pk = invoice_issuer_agency_stamp_id(user)
        if user_is_b2b_agent_or_employee(user):
            if not stamped_agency_pk:
                return queryset.none()
            return queryset.filter(pk=stamped_agency_pk)
        if stamped_agency_pk:
            return queryset.filter(pk=stamped_agency_pk)
        return queryset

    def perform_create(self, serializer):
        created_agency = serializer.save(**self.get_tenant_save_kwargs(serializer))
        create_notifications_for_event(
            entity_type=constants.NotificationEntityTypeChoice.AGENCY,
            action=constants.NotificationActionChoice.CREATED,
            instance=created_agency,
            actor=self.request.user,
        )

    def perform_update(self, serializer):
        updated_agency = serializer.save(**self.get_tenant_save_kwargs(serializer))
        create_notifications_for_event(
            entity_type=constants.NotificationEntityTypeChoice.AGENCY,
            action=constants.NotificationActionChoice.UPDATED,
            instance=updated_agency,
            actor=self.request.user,
        )


class CountryViewSet(StudentPortalReadOnlyMixin, TenantHomeAgencyRowMixin, BaseModelViewSet):
    queryset = Country.objects.select_related("agency", "business").all()
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["business", "agency", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "updated_at", "name"]


class ProgramViewSet(StudentPortalReadOnlyMixin, TenantHomeAgencyRowMixin, BaseModelViewSet):
    queryset = Program.objects.select_related("agency", "business").all()
    serializer_class = ProgramSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["business", "agency", "is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "updated_at", "name"]


class CustomerViewSet(StudentPortalReadOnlyMixin, TenantHomeAgencyRowMixin, BaseModelViewSet):
    queryset = Customer.objects.select_related("agency", "business", "assigned_counselor").all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["business", "agency", "current_status", "file_from", "assigned_counselor", "gender", "is_active"]
    search_fields = ["customer_id", "passport_number", "given_name", "surname", "email", "phone_whatsapp"]
    ordering_fields = ["created_at", "updated_at", "given_name", "current_status"]


class StudentFileViewSet(StudentPortalReadOnlyMixin, TenantHomeAgencyRowMixin, BaseModelViewSet):
    queryset = StudentFile.objects.select_related("agency", "business", "created_by").prefetch_related(
        "attachments",
        "applied_universities",
        "education_background_rows",
        "family_particular_rows",
        "payments",
    ).all()
    serializer_class = StudentFileSerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # ``agency`` is applied in ``get_queryset`` for ``list`` using the same validation as the dashboard.
    filterset_fields = ["business", "current_status", "file_from", "created_by", "is_active"]
    search_fields = ["student_file_id", "passport_number", "given_name", "surname", "email", "phone_whatsapp"]
    ordering_fields = ["created_at", "updated_at", "given_name", "current_status"]
    student_portal_allowed_write_methods = {"PATCH", "PUT"}

    def get_queryset(self):
        """
        Student portal: same row scope as the inventory dashboard (linked file only).

        List for staff: same ``agency`` / ``start_date`` / ``end_date`` rules as
        ``InventoryDashboardAPIView`` (including default rolling 12-month window).
        Non-list actions are not restricted by the dashboard date range so detail
        and writes still resolve historical rows.
        """
        queryset = super().get_queryset()
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return queryset

        if is_student_portal_user(user):
            student_portal_linked_id = getattr(user, "linked_student_file_id", None)
            if student_portal_linked_id:
                return queryset.filter(pk=student_portal_linked_id)
            return queryset.none()

        if self.action != "list":
            return queryset

        query_serializer = InventoryDashboardQuerySerializer(data=self.request.query_params)
        query_serializer.is_valid(raise_exception=True)
        validated_filters = query_serializer.validated_data

        agency = validated_filters.get("agency")
        scoped_business_id = None
        if not user_is_master_admin(user):
            scoped_business_id = tenant_business_id(user)
            if not scoped_business_id or (agency and getattr(agency, "business_id", None) != scoped_business_id):
                agency = None

        if agency:
            queryset = queryset.filter(agency=agency)

        start_date, end_date = inventory_resolve_dashboard_date_range(validated_filters)
        return queryset.filter(created_at__date__range=(start_date, end_date))

    def perform_create(self, serializer):
        if is_student_portal_user(self.request.user):
            raise PermissionDenied("Students cannot create student files directly.")
        created_student_file = serializer.save(**self.get_tenant_save_kwargs(serializer))
        create_notifications_for_event(
            entity_type=constants.NotificationEntityTypeChoice.STUDENT_FILE,
            action=constants.NotificationActionChoice.CREATED,
            instance=created_student_file,
            actor=self.request.user,
        )

    def perform_update(self, serializer):
        updated_student_file = serializer.save(**self.get_tenant_save_kwargs(serializer))
        create_notifications_for_event(
            entity_type=constants.NotificationEntityTypeChoice.STUDENT_FILE,
            action=constants.NotificationActionChoice.UPDATED,
            instance=updated_student_file,
            actor=self.request.user,
        )

    def destroy(self, request, *args, **kwargs):
        if is_student_portal_user(request.user):
            raise PermissionDenied("Students cannot delete student files.")
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        methods=["GET"],
        operation_id="student_files_application_progress_retrieve",
        summary="Get persisted application progress (ordered steps)",
        description=(
            "Returns the **Application Progress** timeline for one student file: ordered steps "
            "with ``state`` (`upcoming` | `in_progress` | `completed`) and ``manual`` (admin lock). "
            "Runs a **sync** from domain data (invoices, document verification, university applications) "
            "into ``StudentApplicationProgress`` before responding; steps with ``manual: true`` are not "
            "overwritten by that sync.\n\n"
            "**Auth:** student (own file only) or staff within tenant scope.\n\n"
            "**Related writes:** staff update underlying data via `PATCH /student-files/{slug}/` "
            "(attachments / applied_universities) and invoices; or override the timeline via PATCH on this URL."
        ),
        responses={200: ApplicationProgressGetSchemaSerializer},
        examples=[
            OpenApiExample(
                "200 — example",
                value={
                    "student_file_id": "STF00012345",
                    "slug": "jane-doe-passport-slug",
                    "current_status": "FILE_RECEIVED",
                    "current_status_label": "File Received",
                    "steps": [
                        {
                            "key": "application_received",
                            "label": "Application Received",
                            "order": 1,
                            "state": "completed",
                            "manual": False,
                        },
                        {
                            "key": "payment_verified",
                            "label": "Payment Verified",
                            "order": 2,
                            "state": "upcoming",
                            "manual": False,
                        },
                        {
                            "key": "enrolled",
                            "label": "Enrolled",
                            "order": 17,
                            "state": "upcoming",
                            "manual": False,
                        },
                    ],
                },
                response_only=True,
            ),
        ],
        tags=["Agency Management — Student files"],
    )
    @extend_schema(
        methods=["PATCH"],
        operation_id="student_files_application_progress_partial_update",
        summary="Update application progress steps (staff)",
        description=(
            "**Staff only** (student portal users receive 403). Body is a JSON object keyed by "
            "step ``key`` (same as ``GET …/steps[].key``). Each value is either a **state string** "
            "(`upcoming` | `in_progress` | `completed`) — which **locks** the step for auto-sync — or "
            "an object ``{ \"state\": \"…\", \"manual\": true|false }``. Use ``manual: false`` to **unlock** "
            "a step so the next sync can overwrite it from invoices/documents/applications again.\n\n"
            "When you set a step to ``completed`` or ``in_progress``, earlier steps become "
            "``completed`` and steps **after** the furthest such step become ``upcoming`` (unless you "
            "include those keys in the same body).\n\n"
            "After a successful PATCH, the server **re-runs sync** for non-locked steps."
        ),
        request=ApplicationProgressPatchSchemaSerializer,
        responses={
            200: ApplicationProgressGetSchemaSerializer,
            403: OpenApiResponse(
                description="Student portal user (PATCH is staff-only for this sub-resource)."
            ),
        },
        examples=[
            OpenApiExample(
                "PATCH — shorthand (locks step)",
                value={"payment_verified": "completed"},
                request_only=True,
            ),
            OpenApiExample(
                "PATCH — explicit + unlock",
                value={
                    "visa_applied": {"state": "in_progress", "manual": True},
                    "documents_verified": {"state": "completed", "manual": False},
                },
                request_only=True,
            ),
        ],
        tags=["Agency Management — Student files"],
    )
    @action(detail=True, methods=["get", "patch"], url_path="application-progress")
    def application_progress(self, request, *args, **kwargs):
        """
        Application tracker aligned with the student portal (full step list in GET).

        Each step has ``state``: ``completed`` | ``in_progress`` | ``upcoming``.
        Persisted on ``StudentApplicationProgress``; staff may ``PATCH`` to set
        a step (optionally locking it from auto sync with ``manual``).
        """
        student_file = self.get_object()
        if request.method == "GET":
            return Response(serialize_application_progress(student_file))
        if is_student_portal_user(request.user):
            raise PermissionDenied("Students cannot update application progress.")
        try:
            normalized = parse_admin_progress_payload(request.data)
        except ValueError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            apply_admin_progress_patch(student_file, normalized)
        except ValueError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serialize_application_progress(student_file))


class UniversityViewSet(StudentPortalReadOnlyMixin, TenantHomeAgencyRowMixin, BaseModelViewSet):
    queryset = University.objects.select_related("country", "agency", "business").prefetch_related(
        Prefetch("intakes", queryset=UniversityIntake.objects.order_by("id")),
        Prefetch(
            "programs",
            queryset=UniversityProgram.objects.select_related("program").prefetch_related(
                Prefetch("subjects", queryset=UniversityProgramSubject.objects.order_by("id"))
            ).order_by("id"),
        ),
    ).all()
    serializer_class = UniversitySerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["business", "country", "agency", "is_active", "programs__program"]
    search_fields = ["university_name", "country__name"]
    ordering_fields = ["created_at", "updated_at", "university_name", "country__name"]


class UniversityIntakeViewSet(StudentPortalReadOnlyMixin, TenantHomeAgencyRowMixin, BaseModelViewSet):
    queryset = UniversityIntake.objects.select_related("university", "university__country", "agency", "business").all()
    serializer_class = UniversityIntakeSerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["business", "university", "agency", "intake_name", "is_active"]
    search_fields = ["intake_name", "university__university_name", "university__country__name"]
    ordering_fields = ["created_at", "updated_at", "intake_name"]


class UniversityProgramViewSet(StudentPortalReadOnlyMixin, TenantHomeAgencyRowMixin, BaseModelViewSet):
    queryset = UniversityProgram.objects.select_related(
        "university", "university__country", "program", "agency", "business"
    ).prefetch_related(
        Prefetch("subjects", queryset=UniversityProgramSubject.objects.order_by("id"))
    )
    serializer_class = UniversityProgramSerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["business", "university", "program", "agency", "is_active"]
    search_fields = ["program__name", "university__university_name", "university__country__name"]
    ordering_fields = ["created_at", "updated_at", "program__name"]


class OfficeCostViewSet(StudentPortalReadOnlyMixin, TenantHomeAgencyRowMixin, BaseModelViewSet):
    queryset = OfficeCost.objects.select_related("agency", "business", "created_by").all()
    serializer_class = OfficeCostSerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["business", "agency", "created_by", "is_active"]
    search_fields = ["title", "description", "agency__name"]
    ordering_fields = ["created_at", "updated_at", "amount", "title"]


class StudentCostViewSet(StudentPortalReadOnlyMixin, TenantHomeAgencyRowMixin, BaseModelViewSet):
    queryset = StudentCost.objects.select_related("agency", "business", "student_file", "created_by").all()
    serializer_class = StudentCostSerializer
    permission_classes = [IsAuthenticated ]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["business", "agency", "student_file", "created_by", "is_active"]
    search_fields = [
        "title",
        "description",
        "student_file__given_name",
        "student_file__surname",
        "student_file__student_file_id",
    ]
    ordering_fields = ["created_at", "updated_at", "amount", "title"]


@extend_schema(
    summary="Hanseo application pack (PDF)",
    description=(
        "Renders ``hanseo.html`` with data from the given student file. "
        "Requires authentication; visibility matches the student-files API."
    ),
    parameters=[
        OpenApiParameter(
            name="student_file_id",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Student file public id (e.g. STF…).",
        ),
        OpenApiParameter(
            name="slug",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Alternate lookup: student file slug.",
        ),
        OpenApiParameter(
            name="id",
            type=int,
            location=OpenApiParameter.QUERY,
            description="Alternate lookup: numeric primary key of the student file.",
        ),
    ],
)
class UniversityFormDownloadAPIView(APIView):
    """
    Renders the Hanseo admission form template to PDF for one ``StudentFile``.

    Pass ``student_file_id`` (recommended) or ``slug`` as query parameters.
    Uses WeasyPrint so ``@page`` and print-oriented CSS in the template are honored.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        student_file_id = (request.query_params.get("student_file_id") or "").strip()
        slug = (request.query_params.get("slug") or "").strip()
        raw_pk = (request.query_params.get("id") or "").strip()
        if not student_file_id and not slug and not raw_pk:
            return Response(
                {"detail": "Provide query parameter student_file_id, slug, or id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = scoped_student_files_queryset(request)
        student_file = None
        if student_file_id:
            student_file = qs.filter(student_file_id=student_file_id).first()
        if student_file is None and slug:
            student_file = qs.filter(slug=slug).first()
        if student_file is None and raw_pk.isdigit():
            student_file = qs.filter(pk=int(raw_pk)).first()
        if student_file is None:
            return Response({"detail": "Student file not found."}, status=status.HTTP_404_NOT_FOUND)

        hanseo_assets_dir = Path(settings.BASE_DIR) / "templates" / "images" / "hanseo"
        asset_base_url = hanseo_assets_dir.as_uri() + "/"
        context = build_hanseo_template_context(student_file)
        html_string = render_to_string(
            "university_templates/hanseo.html",
            context,
            request=request,
        )
        # Import here so a broken WeasyPrint/GTK stack does not prevent the rest of the API from booting.
        from weasyprint import HTML as WeasyHTML

        pdf_bytes = WeasyHTML(string=html_string, base_url=asset_base_url).write_pdf()
        safe_name_part = student_file.student_file_id or str(student_file.pk)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="hanseo-application-{safe_name_part}.pdf"'
        )
        return response


class UniversityFormViewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        student_file = StudentFile.objects.get(student_file_id="STF00000001")

        context = build_hanseo_template_context(student_file)
        html = render_to_string("university_templates/hanseo.html", context, request=request)
        return HttpResponse(html, content_type="text/html")