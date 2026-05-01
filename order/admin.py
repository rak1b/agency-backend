"""Register order domain models with the restricted master admin site."""

from django.contrib import admin

from Config.master_admin_site import master_admin_site

from .models import Invoice, InvoiceAttachment, InvoiceLineItem


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    autocomplete_fields = ("agency", "business")


@admin.register(Invoice, site=master_admin_site)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "invoice_id",
        "business",
        "agency",
        "recipient_type",
        "student",
        "status",
        "issue_date",
        "total_amount",
        "created_by",
        "is_created_by_business_owner",
        "created_at",
        "is_active",
    )
    list_filter = (
        "recipient_type",
        "status",
        "business",
        "agency",
        "is_created_by_business_owner",
        "is_active",
        "is_deleted",
    )
    search_fields = (
        "invoice_id",
        "custom_recipient_name",
        "student__student_file_id",
        "agency__name",
    )
    readonly_fields = ("invoice_id", "slug", "created_at", "updated_at", "subtotal", "total_amount")
    autocomplete_fields = ("business", "agency", "student", "created_by")
    inlines = (InvoiceLineItemInline,)


@admin.register(InvoiceAttachment, site=master_admin_site)
class InvoiceAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "business", "agency", "created_at", "is_active")
    list_filter = ("business", "agency", "is_active", "is_deleted")
    search_fields = ("title", "file_url")
    readonly_fields = ("slug", "created_at", "updated_at")
    autocomplete_fields = ("agency", "business")


@admin.register(InvoiceLineItem, site=master_admin_site)
class InvoiceLineItemAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice", "title", "amount", "created_at", "is_active")
    list_filter = ("business", "agency", "is_active", "is_deleted")
    search_fields = ("title", "invoice__invoice_id")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("invoice", "agency", "business")
