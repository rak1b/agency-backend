from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.utils.translation import gettext_lazy as _

from Config.master_admin_site import master_admin_site

from .models import User, Role, Permission, RolePermission, Merchant, Confirmation, Notification, OauthToken, Section


class AgencyUserChangeForm(UserChangeForm):
    """Django admin change form for the custom ``User`` model (``USERNAME_FIELD`` = email)."""

    class Meta(UserChangeForm.Meta):
        model = User


class CustomUserAdmin(DjangoUserAdmin):
    """
    User admin with password change (hashed) via Django's built-in user admin flow.

    ``UserAdmin`` provides the password reset link and ``AdminPasswordChangeForm`` on the change page.
    """

    model = User
    form = AgencyUserChangeForm

    ordering = ("-created_at",)
    list_display = (
        "email",
        "name",
        "phone",
        "user_type",
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    )
    search_fields = (
        "email",
        "name",
        "phone",
        "slug",
        "user_id",
        "employee_id",
        "designation",
        "role__name",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "user_type",
        "is_verified",
        "is_approved",
        "created_at",
    )
    filter_horizontal = ("groups", "role", "user_permissions")
    readonly_fields = ("id", "slug", "user_id", "created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "name",
                    "phone",
                    "image_url",
                    "dob",
                    "gender",
                    "address",
                )
            },
        ),
        (
            _("Organization"),
            {
                "fields": (
                    "slug",
                    "user_id",
                    "role",
                    "user_type",
                    "parent_agency",
                    "parent_business",
                    "parent_b2b_agent",
                    "linked_student_file",
                    "employee_id",
                    "designation",
                    "trade_license_no",
                    "commission_rate",
                    "contract_start_date",
                    "contract_end_date",
                    "joining_date",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                    "is_verified",
                    "is_approved",
                )
            },
        ),
        (
            _("Activity"),
            {
                "fields": ("last_login", "last_login_ip", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "name"),
            },
        ),
    )


class RoleAdmin(admin.ModelAdmin):
    """Admin for Role model to enable autocomplete."""

    search_fields = ("name", "description")
    list_display = ("id", "name", "description", "created_at")
    list_filter = ("created_at",)


master_admin_site.register(User, CustomUserAdmin)
master_admin_site.register(Role, RoleAdmin)
master_admin_site.register(Permission)
master_admin_site.register(RolePermission)
master_admin_site.register(OauthToken)
master_admin_site.register(Merchant)
master_admin_site.register(Confirmation)
master_admin_site.register(Notification)
master_admin_site.register(Section)
