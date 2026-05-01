from decimal import Decimal

from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authentication.base import BaseModelViewSet, StudentPortalReadOnlyMixin

from ...constants import InvoiceStatusChoice, RecipientTypeChoice
from ...models import Invoice
from .serializers import (
    InvoiceReportQuerySerializer,
    InvoiceReportResponseSerializer,
    InvoiceSerializer,
)


def _decimal_zero():
    return Value(Decimal("0.00"))


def _money_aggregate_field():
    return DecimalField(max_digits=12, decimal_places=2)


def _invoice_report_openapi_parameters():
    """Query params mirrored in Swagger for ``GET /invoices/report/`` (same as list filters + dates)."""
    ordering_hint = (
        "Comma-separated. Allowed: created_at, -created_at, updated_at, -updated_at, "
        "issue_date, -issue_date, due_date, -due_date, total_amount, -total_amount, status, -status."
    )
    return [
        OpenApiParameter(
            name="issue_date_from",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Inclusive lower bound on invoice ``issue_date``.",
        ),
        OpenApiParameter(
            name="issue_date_to",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Inclusive upper bound on invoice ``issue_date``.",
        ),
        OpenApiParameter(
            name="recipient_type",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            enum=[c.value for c in RecipientTypeChoice],
            description="Exact match on invoice recipient type.",
        ),
        OpenApiParameter(
            name="status",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            enum=[c.value for c in InvoiceStatusChoice],
            description="Exact match on invoice status.",
        ),
        OpenApiParameter(
            name="agency",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Primary key of the related agency.",
        ),
        OpenApiParameter(
            name="student",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Primary key of the related student file.",
        ),
        OpenApiParameter(
            name="created_by",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Primary key of the user who created the invoice.",
        ),
        OpenApiParameter(
            name="is_active",
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filter by soft-delete visibility flag on the invoice record.",
        ),
        OpenApiParameter(
            name="search",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description=(
                "Case-insensitive search across ``invoice_id``, agency name, student given/surname, "
                "and ``custom_recipient_name``."
            ),
        ),
        OpenApiParameter(
            name="ordering",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description=ordering_hint,
        ),
    ]


def _invoice_group_breakdown(queryset, field_name, label_map):
    """
    Build status- or recipient-type-style rows with money totals per bucket.
    """
    zero = _decimal_zero()
    money = _money_aggregate_field()
    rows = (
        queryset.values(field_name)
        .annotate(
            count=Count("id"),
            subtotal=Coalesce(Sum("subtotal"), zero, output_field=money),
            vat_amount=Coalesce(Sum("vat_amount"), zero, output_field=money),
            total_amount=Coalesce(Sum("total_amount"), zero, output_field=money),
        )
        .order_by(field_name)
    )
    out = []
    for row in rows:
        key = row[field_name]
        key_str = key if key is not None else ""
        out.append(
            {
                "key": key_str,
                "label": str(label_map.get(key, key_str or "")),
                "count": row["count"],
                "subtotal": row["subtotal"],
                "vat_amount": row["vat_amount"],
                "total_amount": row["total_amount"],
            }
        )
    return out


class InvoiceViewSet(StudentPortalReadOnlyMixin, BaseModelViewSet):
    queryset = Invoice.objects.select_related("agency", "business", "student", "created_by").prefetch_related(
        "attachments",
        "line_items",
    )
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["recipient_type", "status", "agency", "student", "created_by", "is_active"]
    search_fields = [
        "invoice_id",
        "agency__name",
        "student__given_name",
        "student__surname",
        "custom_recipient_name",
    ]
    ordering_fields = ["created_at", "updated_at", "issue_date", "due_date", "total_amount", "status"]

    @extend_schema(
        summary="Invoice aggregates report",
        description=(
            "Returns counts and money totals for the current filtered invoice set, "
            "plus breakdowns by status and recipient type. "
            "Supports the same query filters as the invoice list (``recipient_type``, ``status``, "
            "``agency``, ``student``, ``created_by``, ``is_active``, ``search``, ``ordering``) "
            "and optional ``issue_date_from`` / ``issue_date_to`` (inclusive) on ``issue_date``."
        ),
        parameters=_invoice_report_openapi_parameters(),
        responses={status.HTTP_200_OK: InvoiceReportResponseSerializer},
    )
    @action(detail=False, methods=["get"], url_path="report")
    def report(self, request, *args, **kwargs):
        query = InvoiceReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        issue_date_from = query.validated_data.get("issue_date_from")
        issue_date_to = query.validated_data.get("issue_date_to")

        base = self.filter_queryset(self.get_queryset())
        if issue_date_from is not None:
            base = base.filter(issue_date__gte=issue_date_from)
        if issue_date_to is not None:
            base = base.filter(issue_date__lte=issue_date_to)

        zero = _decimal_zero()
        money = _money_aggregate_field()
        summary = base.aggregate(
            invoice_count=Count("id"),
            subtotal_sum=Coalesce(Sum("subtotal"), zero, output_field=money),
            vat_amount_sum=Coalesce(Sum("vat_amount"), zero, output_field=money),
            total_amount_sum=Coalesce(Sum("total_amount"), zero, output_field=money),
        )

        status_labels = dict(InvoiceStatusChoice.choices)
        recipient_labels = dict(RecipientTypeChoice.choices)

        tracked_filter_keys = (
            "issue_date_from",
            "issue_date_to",
            "recipient_type",
            "status",
            "agency",
            "student",
            "created_by",
            "is_active",
            "search",
            "ordering",
        )
        filters_applied = {key: request.query_params.get(key) for key in tracked_filter_keys if request.query_params.get(key)}

        payload = {
            "filters": filters_applied,
            "summary": {
                "invoice_count": summary["invoice_count"],
                "subtotal_sum": summary["subtotal_sum"],
                "vat_amount_sum": summary["vat_amount_sum"],
                "total_amount_sum": summary["total_amount_sum"],
            },
            "by_status": _invoice_group_breakdown(base, "status", status_labels),
            "by_recipient_type": _invoice_group_breakdown(base, "recipient_type", recipient_labels),
        }
        return Response(payload, status=status.HTTP_200_OK)
