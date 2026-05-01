"""
Helpers for multi-tenant access control (business → student row scope).

Master operators use Django ``is_superuser`` and bypass tenant filters everywhere.
"""

from django.core.exceptions import FieldDoesNotExist

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


def user_is_b2b_agent_or_employee(user) -> bool:
    """Inventory users tied to a single agency (B2B partner or their staff)."""
    if not user or not user.is_authenticated:
        return False
    ut = getattr(user, "user_type", None)
    return ut in (
        constants.UserTypeChoice.B2B_AGENT,
        constants.UserTypeChoice.B2B_AGENT_EMPLOYEE,
    )


def b2b_agent_tenant_agency_id(user):
    """
    Agency used to scope rows for B2B users.

    ``B2B_AGENT`` uses ``parent_agency``. ``B2B_AGENT_EMPLOYEE`` prefers the parent
    agent's agency, then falls back to the employee's own ``parent_agency`` if set.
    """
    if not user or not user.is_authenticated:
        return None
    ut = getattr(user, "user_type", None)
    if ut == constants.UserTypeChoice.B2B_AGENT:
        return getattr(user, "parent_agency_id", None)
    if ut == constants.UserTypeChoice.B2B_AGENT_EMPLOYEE:
        parent = getattr(user, "parent_b2b_agent", None)
        if parent is not None and getattr(parent, "parent_agency_id", None):
            return parent.parent_agency_id
        return getattr(user, "parent_agency_id", None)
    return None


def model_has_agency_fk(model_class) -> bool:
    """True if the model defines a field named ``agency`` (typical FK to ``Agency``)."""
    try:
        model_class._meta.get_field("agency")
        return True
    except FieldDoesNotExist:
        return False


def apply_b2b_agency_scope_to_queryset(queryset, user):
    """
    After business-level tenant scope, narrow rows to the B2B user's agency.

    Agency super admins and employees (non-B2B user types) keep business-wide access
    within their tenant. B2B agents and their staff only see rows for their
    ``parent_agency`` (see ``b2b_agent_tenant_agency_id``).
    """
    if not user or not user.is_authenticated or user_is_master_admin(user):
        return queryset
    if not user_is_b2b_agent_or_employee(user):
        return queryset
    if not model_has_agency_fk(queryset.model):
        return queryset
    agency_id = b2b_agent_tenant_agency_id(user)
    if not agency_id:
        return queryset.none()
    return queryset.filter(agency_id=agency_id)


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

