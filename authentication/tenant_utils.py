"""
Helpers for multi-tenant access control (business → student row scope).

Master operators use Django ``is_superuser`` and bypass tenant filters everywhere.
"""

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q

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


def invoice_issuer_agency_stamp_id(user):
    """
    Primary key of the agency to store on an **issued** invoice when the row
    needs the creator's desk/context (e.g. ``CUSTOM`` recipient).

    B2B users use the same resolution as ``b2b_agent_tenant_agency_id``;
    agency-side staff use ``User.parent_agency`` when set.
    """
    if not user or not user.is_authenticated:
        return None
    if user_is_b2b_agent_or_employee(user):
        return b2b_agent_tenant_agency_id(user)
    return getattr(user, "parent_agency_id", None)


def invoice_requires_business_staff_flag_filter(user) -> bool:
    """
    ``AGENCY_SUPER_ADMIN`` / ``AGENCY_EMPLOYEE`` users only see invoices with
    ``Invoice.is_created_by_business_owner`` set, excluding B2B-originated rows.
    """
    if not user or not user.is_authenticated or user_is_master_admin(user):
        return False
    if is_student_portal_user(user):
        return False
    ut = getattr(user, "user_type", None)
    return ut in (
        constants.UserTypeChoice.AGENCY_SUPER_ADMIN,
        constants.UserTypeChoice.AGENCY_EMPLOYEE,
    )


def invoice_list_skips_agency_row_scope(user) -> bool:
    """
    When True (default for non-B2B), invoice APIs only enforce ``business_id`` after
    ``BaseModelViewSet`` — **no extra filter on Invoice.agency**.

    - ``AGENCY_SUPER_ADMIN`` / ``AGENCY_EMPLOYEE``: business-wide under ``parent_business``.
    - ``B2B_AGENT`` / ``B2B_AGENT_EMPLOYEE``: callers apply ``apply_b2b_agency_scope_to_queryset``
      so rows match the partner's scoped agency.

    Unknown or unset ``user_type`` is treated like agency-side staff (business-only invoices).
    """
    if not user or not user.is_authenticated:
        return True
    if user_is_master_admin(user):
        return True
    if is_student_portal_user(user):
        return True
    ut = getattr(user, "user_type", None)
    return ut not in (
        constants.UserTypeChoice.B2B_AGENT,
        constants.UserTypeChoice.B2B_AGENT_EMPLOYEE,
    )


def model_has_agency_fk(model_class) -> bool:
    """True if the model defines a field named ``agency`` (typical FK to ``Agency``)."""
    try:
        model_class._meta.get_field("agency")
        return True
    except FieldDoesNotExist:
        return False


def apply_b2b_agency_scope_to_queryset(queryset, user, *, include_null_agency_created_by_user=False):
    """
    After business isolation, optionally narrow rows to the user's **home agency**
    whenever one can be resolved (``invoice_issuer_agency_stamp_id``).

    Tenants whose users have ``parent_agency`` (or are B2B with a scoped agency)
    always see sibling rows only within that agency. Users with only ``parent_business``
    and no home agency retain business-wide access within that business.

    B2B agents/employees whose agency cannot be resolved get an empty queryset
    (their account is mis-linked).

    Students skip this layer (caller still applies business / portal rules elsewhere).

    When ``include_null_agency_created_by_user`` applies (Invoice legacy rows), orphaned
    ``agency=NULL`` rows created by ``user`` may still appear.
    """
    if not user or not user.is_authenticated or user_is_master_admin(user):
        return queryset
    if is_student_portal_user(user):
        return queryset

    stamp_agency_id = invoice_issuer_agency_stamp_id(user)

    # B2B accounts must never fall back to business-wide rows.
    if user_is_b2b_agent_or_employee(user):
        if not stamp_agency_id:
            return queryset.none()
    elif not stamp_agency_id:
        return queryset

    if not model_has_agency_fk(queryset.model):
        return queryset

    agency_scope_id = stamp_agency_id

    if not include_null_agency_created_by_user:
        return queryset.filter(agency_id=agency_scope_id)

    try:
        queryset.model._meta.get_field("created_by")
    except FieldDoesNotExist:
        return queryset.filter(agency_id=agency_scope_id)

    return queryset.filter(Q(agency_id=agency_scope_id) | Q(agency__isnull=True, created_by=user))


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

