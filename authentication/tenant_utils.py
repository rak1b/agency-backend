"""
Helpers for multi-tenant access control (business → agency → student row scope).

Master operators use Django ``is_superuser`` and bypass tenant filters everywhere.
"""

from authentication import constants


def user_is_master_admin(user) -> bool:
    """Platform operator: full access (Django admin + all API rows)."""
    return bool(user and user.is_authenticated and getattr(user, "is_superuser", False))


def is_student_portal_user(user) -> bool:
    """Agency student logging into the portal (row-level scope to one student file)."""
    return bool(
        user
        and user.is_authenticated
        and getattr(user, "user_type", None) == constants.UserTypeChoice.STUDENT
    )


def tenant_agency_id(user):
    """
    Preferred agency primary key for the authenticated tenant user, or None if not linked.

    Students may omit ``parent_agency`` if ``linked_student_file`` is set; the
    agency is then taken from that file.
    """
    if not user or not user.is_authenticated:
        return None
    direct = getattr(user, "parent_agency_id", None)
    if direct:
        return direct
    if is_student_portal_user(user) and getattr(user, "linked_student_file_id", None):
        from agency_inventory.models import StudentFile

        return (
            StudentFile.objects.filter(pk=user.linked_student_file_id)
            .values_list("agency_id", flat=True)
            .first()
        )
    return None


def tenant_business_id(user):
    """
    Top-level tenant key: ``User.parent_business``, else inferred from agency or linked student file.
    """
    if not user or not user.is_authenticated:
        return None
    direct = getattr(user, "parent_business_id", None)
    if direct:
        return direct
    parent_agency_pk = getattr(user, "parent_agency_id", None)
    if parent_agency_pk:
        from agency_inventory.models import Agency

        return (
            Agency.objects.filter(pk=parent_agency_pk)
            .values_list("business_id", flat=True)
            .first()
        )
    if is_student_portal_user(user) and getattr(user, "linked_student_file_id", None):
        from agency_inventory.models import StudentFile

        return (
            StudentFile.objects.filter(pk=user.linked_student_file_id)
            .values_list("business_id", flat=True)
            .first()
        )
    return None


def tenant_org_save_kwargs(user, model_class, has_field_fn) -> dict:
    """
    Merge into ``serializer.save(...)`` so tenant users persist the correct ``business_id``
    and ``agency_id`` (kwargs override validated_data in DRF).
    """
    if user_is_master_admin(user):
        return {}
    kwargs = {}
    business_id = tenant_business_id(user)
    agency_id = tenant_agency_id(user)
    if business_id and has_field_fn(model_class, "business"):
        kwargs["business_id"] = business_id
    if agency_id and has_field_fn(model_class, "agency"):
        kwargs["agency_id"] = agency_id
    return kwargs


def tenant_agency_save_kwargs(user, model_class, has_field_fn) -> dict:
    """Backward-compatible alias for code that still imports the old name."""
    return tenant_org_save_kwargs(user, model_class, has_field_fn)
