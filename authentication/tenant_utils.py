"""
Helpers for multi-tenant access control (business → student row scope).

Master operators use Django ``is_superuser`` and bypass tenant filters everywhere.
"""

from authentication import constants


def user_is_master_admin(user) -> bool:
    """Platform operator: full access (Django admin + all API rows)."""
    return bool(user and user.is_authenticated and getattr(user, "is_superuser", False))


def is_student_portal_user(user) -> bool:
    """Business student logging into the portal (row-level scope to one student file)."""
    return bool(
        user
        and user.is_authenticated
        and getattr(user, "user_type", None) == constants.UserTypeChoice.STUDENT
    )

def tenant_business_id(user):
    """
    Top-level tenant key. Tenant visibility is based on the user's explicit business.
    """
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "parent_business_id", None)


def tenant_org_save_kwargs(user, model_class, has_field_fn) -> dict:
    """
    Merge into ``serializer.save(...)`` so tenant users persist the correct ``business_id``.

    Agency is a normal relationship inside a business, not the tenant boundary.
    """
    if user_is_master_admin(user):
        return {}
    kwargs = {}
    business_id = tenant_business_id(user)
    if business_id and has_field_fn(model_class, "business"):
        kwargs["business_id"] = business_id
    return kwargs

