from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated

from authentication.base import BaseModelViewSet

from ...models import Invoice
from .serializers import InvoiceSerializer


class InvoiceViewSet(BaseModelViewSet):
    queryset = Invoice.objects.select_related("agency", "student", "created_by").prefetch_related(
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
