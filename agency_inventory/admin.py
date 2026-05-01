from django.contrib import admin
from django.contrib.admin import register

from Config.master_admin_site import master_admin_site

from .models import (
    Agency,
    Business,
    Customer,
    StudentFile,
    University,
    UniversityIntake,
    UniversityProgram,
    UniversityProgramSubject,
)


@register(Business, site=master_admin_site)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner_name", "status", "business_email", "phone", "created_at", "is_active")
    search_fields = ("name", "owner_name", "business_email")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(Agency, site=master_admin_site)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "name", "owner_name", "status", "business_email", "phone", "created_at", "is_active")
    list_filter = ("status", "is_active", "is_deleted")
    search_fields = ("name", "owner_name", "business_email", "phone")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(Customer, site=master_admin_site)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_id", "given_name", "surname", "agency", "current_status", "passport_number", "created_at")
    list_filter = ("current_status", "gender", "agency", "file_from", "is_active", "is_deleted")
    search_fields = ("customer_id", "passport_number", "given_name", "surname", "email", "phone_whatsapp")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(StudentFile, site=master_admin_site)
class StudentFileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student_file_id",
        "given_name",
        "surname",
        "agency",
        "current_status",
        "passport_number",
        "created_at",
    )
    list_filter = ("current_status", "agency", "file_from", "is_active", "is_deleted")
    search_fields = ("student_file_id", "passport_number", "given_name", "surname", "email", "phone_whatsapp")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(University, site=master_admin_site)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ("id", "university_name", "agency", "country", "created_at", "is_active")
    list_filter = ("agency", "country", "is_active", "is_deleted")
    search_fields = ("university_name", "country__name", "agency__name")
    readonly_fields = ("slug", "created_at", "updated_at")


@register(UniversityIntake, site=master_admin_site)
class UniversityIntakeAdmin(admin.ModelAdmin):
    list_display = ("id", "university", "intake_name", "created_at", "is_active")
    list_filter = ("university", "is_active", "is_deleted")
    search_fields = ("university__university_name", "intake_name")


class UniversityProgramSubjectInline(admin.TabularInline):
    model = UniversityProgramSubject
    extra = 0


@register(UniversityProgram, site=master_admin_site)
class UniversityProgramAdmin(admin.ModelAdmin):
    list_display = ("id", "university", "program", "created_at", "is_active")
    list_filter = ("university", "program", "is_active", "is_deleted")
    search_fields = ("university__university_name", "program")
    inlines = (UniversityProgramSubjectInline,)
