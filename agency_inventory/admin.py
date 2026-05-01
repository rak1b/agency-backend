from django.contrib import admin
from django.contrib.admin import register

from Config.master_admin_site import master_admin_site

from .models import (
    Agency,
    AppliedUniversity,
    Business,
    Country,
    Customer,
    OfficeCost,
    Program,
    StudentCost,
    StudentFile,
    StudentFileAttachment,
    University,
    UniversityIntake,
    UniversityProgram,
    UniversityProgramSubject,
)


@register(Business, site=master_admin_site)
class BusinessAdmin(admin.ModelAdmin):
    """Root tenant entity; no ``business`` FK on this model."""

    list_display = ("id", "name", "owner_name", "status", "business_email", "phone", "created_at", "is_active")
    list_filter = ("status", "is_active", "is_deleted")
    search_fields = ("name", "owner_name", "business_email")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(Agency, site=master_admin_site)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "name", "owner_name", "status", "business_email", "phone", "created_at", "is_active")
    list_filter = ("business", "status", "is_active", "is_deleted")
    search_fields = ("name", "owner_name", "business_email", "phone")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(Program, site=master_admin_site)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "name", "agency", "created_at", "is_active")
    list_filter = ("business", "agency", "is_active", "is_deleted")
    search_fields = ("name", "agency__name")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(Country, site=master_admin_site)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "name", "agency", "created_at", "is_active")
    list_filter = ("business", "agency", "is_active", "is_deleted")
    search_fields = ("name", "agency__name")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(Customer, site=master_admin_site)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "customer_id", "given_name", "surname", "agency", "current_status", "passport_number", "created_at")
    list_filter = ("business", "current_status", "gender", "agency", "file_from", "is_active", "is_deleted")
    search_fields = ("customer_id", "passport_number", "given_name", "surname", "email", "phone_whatsapp")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(StudentFile, site=master_admin_site)
class StudentFileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "business",
        "student_file_id",
        "given_name",
        "surname",
        "agency",
        "current_status",
        "passport_number",
        "created_at",
    )
    list_filter = ("business", "current_status", "agency", "file_from", "is_active", "is_deleted")
    search_fields = ("student_file_id", "passport_number", "given_name", "surname", "email", "phone_whatsapp")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(StudentFileAttachment, site=master_admin_site)
class StudentFileAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "title", "agency", "created_at", "is_active")
    list_filter = ("business", "agency", "is_active", "is_deleted")
    search_fields = ("title", "file_url", "agency__name")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(AppliedUniversity, site=master_admin_site)
class AppliedUniversityAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "university", "country", "agency", "intake", "created_at", "is_active")
    list_filter = ("business", "agency", "is_active", "is_deleted")
    search_fields = ("intake", "university__university_name", "country__name")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(University, site=master_admin_site)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "university_name", "agency", "country", "created_at", "is_active")
    list_filter = ("business", "agency", "country", "is_active", "is_deleted")
    search_fields = ("university_name", "country__name", "agency__name")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(UniversityIntake, site=master_admin_site)
class UniversityIntakeAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "university", "intake_name", "created_at", "is_active")
    list_filter = ("business", "university", "is_active", "is_deleted")
    search_fields = ("university__university_name", "intake_name")
    readonly_fields = ("slug", "created_at", "updated_at")


class UniversityProgramSubjectInline(admin.TabularInline):
    model = UniversityProgramSubject
    extra = 0
    fields = ("business", "subject_name", "track_name", "slug", "is_active")
    # Business is derived from the parent program; keep it visible but not editable inline.
    readonly_fields = ("slug", "business")
    show_change_link = True


@register(UniversityProgram, site=master_admin_site)
class UniversityProgramAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "university", "program", "created_at", "is_active")
    list_filter = ("business", "university", "program", "is_active", "is_deleted")
    search_fields = ("university__university_name", "program__name")
    readonly_fields = ("slug", "created_at", "updated_at")
    inlines = (UniversityProgramSubjectInline,)


@register(UniversityProgramSubject, site=master_admin_site)
class UniversityProgramSubjectAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "program", "subject_name", "track_name", "created_at", "is_active")
    list_filter = ("business", "program", "is_active", "is_deleted")
    search_fields = ("subject_name", "track_name", "program__university__university_name")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(OfficeCost, site=master_admin_site)
class OfficeCostAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "title", "agency", "amount", "created_at", "is_active")
    list_filter = ("business", "agency", "is_active", "is_deleted")
    search_fields = ("title", "description", "agency__name")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(StudentCost, site=master_admin_site)
class StudentCostAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "title", "student_file", "agency", "amount", "created_at", "is_active")
    list_filter = ("business", "agency", "student_file", "is_active", "is_deleted")
    search_fields = ("title", "description", "student_file__student_file_id", "student_file__given_name")
    readonly_fields = ("slug", "created_at", "updated_at")
