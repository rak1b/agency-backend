from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authentication.base import BaseModelViewSet

from ...models import Ticket
from .serializers import (
    TicketReplyCreatedSerializer,
    TicketReplyPayloadSerializer,
    TicketSerializer,
)


class TicketViewSet(BaseModelViewSet):
    queryset = Ticket.objects.select_related(
        "created_by",
        "agency",
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
    filterset_fields = ["status", "priority", "creator_type", "agency", "student_file", "created_by", "is_active"]
    search_fields = ["ticket_id", "subject", "description", "created_by__name", "created_by__email"]
    ordering_fields = ["created_at", "updated_at", "last_replied_at", "status", "priority"]

    def get_serializer_class(self):
        if self.action == "reply":
            return TicketReplyPayloadSerializer
        return TicketSerializer

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

        ticket_serializer = self.get_serializer(instance=ticket)
        reply_instance = ticket_serializer.create_reply(
            ticket=ticket,
            validated_data=payload_serializer.validated_data,
        )
        return Response(
            {
                "message": "Reply created successfully.",
                "reply_id": reply_instance.id,
                "ticket": self.get_serializer(ticket).data,
            },
            status=status.HTTP_201_CREATED,
        )
