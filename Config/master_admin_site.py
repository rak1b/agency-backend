"""
Django admin site restricted to platform master operators (``is_superuser`` only).

Agency staff use the REST API / separate panel; they must not access this admin.
"""

from django.contrib.admin.sites import AdminSite


class MasterAdminSite(AdminSite):
    """Only active superusers may access the admin index and model pages."""

    site_header = "Agency platform administration"
    site_title = "Master admin"

    def has_permission(self, request):
        user = request.user
        return bool(
            user
            and user.is_active
            and user.is_authenticated
            and getattr(user, "is_superuser", False)
        )


master_admin_site = MasterAdminSite(name="master_admin")
