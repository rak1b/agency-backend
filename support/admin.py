"""Register support domain models with the restricted master admin site."""

from django.contrib import admin

from Config.master_admin_site import master_admin_site

from .models import Ticket, TicketAttachment, TicketReply


class TicketReplyInline(admin.TabularInline):
    model = TicketReply
    extra = 0
    autocomplete_fields = ("agency", "business", "replied_by")
    ordering = ("created_at",)


@admin.register(Ticket, site=master_admin_site)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "ticket_id",
        "subject",
        "business",
        "agency",
        "student_file",
        "creator_type",
        "status",
        "priority",
        "created_by",
        "created_at",
        "is_active",
    )
    list_filter = ("creator_type", "status", "priority", "business", "agency", "is_active", "is_deleted")
    search_fields = ("ticket_id", "subject", "description", "created_by__email", "student_file__student_file_id")
    readonly_fields = ("ticket_id", "slug", "created_at", "updated_at")
    autocomplete_fields = ("business", "agency", "student_file", "created_by", "last_reply_by")
    inlines = (TicketReplyInline,)


@admin.register(TicketReply, site=master_admin_site)
class TicketReplyAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "business", "agency", "replied_by", "created_at", "is_active")
    list_filter = ("business", "agency", "is_active", "is_deleted")
    search_fields = ("message", "ticket__ticket_id")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("ticket", "agency", "business", "replied_by")


@admin.register(TicketAttachment, site=master_admin_site)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "file_name", "business", "agency", "ticket", "reply", "created_at", "is_active")
    list_filter = ("business", "agency", "is_active", "is_deleted")
    search_fields = ("file_name", "file_url", "ticket__ticket_id")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("ticket", "reply", "agency", "business", "uploaded_by")
