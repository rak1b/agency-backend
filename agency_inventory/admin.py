from django.contrib import admin

from .models import Agency, Customer, University, UniversityIntake, UniversityProgram


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner_name", "status", "business_email", "phone", "created_at", "is_active")
    list_filter = ("status", "is_active", "is_deleted")
    search_fields = ("name", "owner_name", "business_email", "phone")
    readonly_fields = ("slug", "created_at", "updated_at")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_id", "given_name", "surname", "agency", "current_status", "passport_number", "created_at")
    list_filter = ("current_status", "gender", "agency", "file_from", "is_active", "is_deleted")
    search_fields = ("customer_id", "passport_number", "given_name", "surname", "email", "phone_whatsapp")
    readonly_fields = ("slug", "created_at", "updated_at")


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "country", "created_at", "is_active")
    list_filter = ("country", "is_active", "is_deleted")
    search_fields = ("name", "country")
    readonly_fields = ("slug", "created_at", "updated_at")


@admin.register(UniversityIntake)
class UniversityIntakeAdmin(admin.ModelAdmin):
    list_display = ("id", "university", "intake_name", "created_at", "is_active")
    list_filter = ("university", "is_active", "is_deleted")
    search_fields = ("university__name", "intake_name")


@admin.register(UniversityProgram)
class UniversityProgramAdmin(admin.ModelAdmin):
    list_display = ("id", "university", "program", "created_at", "is_active")
    list_filter = ("university", "program", "is_active", "is_deleted")
    search_fields = ("university__name", "program")
