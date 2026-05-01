from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response

from authentication.base import BaseModelViewSet
from authentication.tenant_utils import apply_b2b_agency_scope_to_queryset, is_student_portal_user

from ...models import Ticket
from .serializers import (
    TicketReplyCreatedSerializer,
    TicketReplyPayloadSerializer,
    TicketSerializer,
)


class TicketViewSet(BaseModelViewSet):
    """
    Students may POST new tickets and POST ``reply``; other mutating verbs are blocked.
    """

    queryset = Ticket.objects.select_related(
        "created_by",
        "agency",
        "business",
        "student_file",
        "last_reply_by",
    ).prefetch_related(
        "attachments",
        "replies",
        "replies__attachments",
        "replies__replied_by",
    )
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["business", "status", "priority", "creator_type", "agency", "student_file", "created_by", "is_active"]
    search_fields = ["ticket_id", "subject", "description", "created_by__name", "created_by__email"]
    ordering_fields = ["created_at", "updated_at", "last_replied_at", "status", "priority"]

    def _apply_tenant_scope(self, queryset):
        queryset = super()._apply_tenant_scope(queryset)
        return apply_b2b_agency_scope_to_queryset(queryset, getattr(self.request, "user", None))

    def dispatch(self, request, *args, **kwargs):
        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and is_student_portal_user(user)
            and request.method not in SAFE_METHODS
            and request.method != "POST"
        ):
            raise PermissionDenied("Students may only create tickets or add replies (POST).")
        return super().dispatch(request, *args, **kwargs)

    @extend_schema(
        request=TicketReplyPayloadSerializer,
        responses={201: TicketReplyCreatedSerializer},
        description="Append a reply to the ticket with optional message text, URL-based attachments, "
        "and/or multipart files under the field name `attachments_files`.",
    )
    @action(detail=True, methods=["post"], url_path="reply")
    def reply(self, request, *args, **kwargs):
        ticket = self.get_object()
        payload_serializer = TicketReplyPayloadSerializer(
            data=request.data,
            context={"request": request},
        )
        payload_serializer.is_valid(raise_exception=True)

        serializer_context = self.get_serializer_context()
        ticket_serializer = TicketSerializer(instance=ticket, context=serializer_context)
        reply_instance = ticket_serializer.create_reply(
            ticket=ticket,
            validated_data=payload_serializer.validated_data,
        )
        # Ticket may have been prefetched without this reply; drop cache so nested `reply_details` is fresh.
        if hasattr(ticket, "_prefetched_objects_cache") and "replies" in ticket._prefetched_objects_cache:
            del ticket._prefetched_objects_cache["replies"]

        return Response(
            {
                "message": "Reply created successfully.",
                "reply_id": reply_instance.id,
                "ticket": TicketSerializer(instance=ticket, context=serializer_context).data,
            },
            status=status.HTTP_201_CREATED,
        )
