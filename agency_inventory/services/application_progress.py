"""
Application progress tracker: compute rules, persist on ``StudentApplicationProgress``,
and expose a stable JSON shape for the student portal.

See ``StudentApplicationProgress`` on ``agency_inventory.models`` for stored fields.
"""

from __future__ import annotations

from typing import Any

from django.apps import apps

from agency_inventory.constants import ApplicationProgressStepState, ReviewStatusChoice

# Plain strings match ``ApplicationProgressStepState`` DB values. Django stubs type
# ``TextChoices`` members as tuple literals, so use explicit strings for ``list[str]``.
ST_UPCOMING: str = "upcoming"
ST_IN_PROGRESS: str = "in_progress"
ST_COMPLETED: str = "completed"

# (api_key, human label, model state field name, model manual lock field name)
STEP_DEFINITIONS: tuple[tuple[str, str, str, str], ...] = (
    ("application_received", "Application Received", "application_received", "application_received_manual"),
    ("payment_verified", "Payment Verified", "payment_verified", "payment_verified_manual"),
    ("documents_under_review", "Documents Under Review", "documents_under_review", "documents_under_review_manual"),
    ("documents_verified", "Documents Verified", "documents_verified", "documents_verified_manual"),
    ("university_applied", "University Applied", "university_applied", "university_applied_manual"),
    ("visa_applied", "Visa Applied", "visa_applied", "visa_applied_manual"),
    ("visa_approved", "Visa Approved", "visa_approved", "visa_approved_manual"),
    ("admitted", "Admitted", "admitted", "admitted_manual"),
)

STEP_KEYS: tuple[str, ...] = tuple(row[0] for row in STEP_DEFINITIONS)


def _invoice_model():
    return apps.get_model("order", "Invoice")


def _payment_step_state(student_file) -> str:
    Invoice = _invoice_model()
    rows = list(Invoice.all_objects.filter(student_id=student_file.pk).values("status"))
    if not rows:
        return ST_UPCOMING
    if any((r.get("status") or "").lower() == "paid" for r in rows):
        return ST_COMPLETED
    return ST_IN_PROGRESS


def _documents_under_review_state(student_file) -> str:
    rows = list(
        student_file.attachments.filter(file_url__isnull=False)
        .exclude(file_url="")
        .values("verification_status")
    )
    if not rows:
        return ST_UPCOMING
    pending = sum(
        1
        for r in rows
        if (r.get("verification_status") or ReviewStatusChoice.PENDING) == ReviewStatusChoice.PENDING
    )
    if pending > 0:
        return ST_IN_PROGRESS
    return ST_COMPLETED


def _documents_verified_state(student_file) -> str:
    rows = list(
        student_file.attachments.filter(file_url__isnull=False)
        .exclude(file_url="")
        .values("verification_status")
    )
    if not rows:
        return ST_UPCOMING
    pending = sum(
        1
        for r in rows
        if (r.get("verification_status") or ReviewStatusChoice.PENDING) == ReviewStatusChoice.PENDING
    )
    if pending > 0:
        return ST_UPCOMING
    approved = sum(1 for r in rows if r.get("verification_status") == ReviewStatusChoice.APPROVED)
    if approved == len(rows):
        return ST_COMPLETED
    return ST_IN_PROGRESS


def _university_applied_state(student_file) -> str:
    rows = list(student_file.applied_universities.values("application_status"))
    if not rows:
        return ST_UPCOMING
    pending = sum(
        1
        for r in rows
        if (r.get("application_status") or ReviewStatusChoice.PENDING) == ReviewStatusChoice.PENDING
    )
    if pending > 0:
        return ST_IN_PROGRESS
    approved = sum(1 for r in rows if r.get("application_status") == ReviewStatusChoice.APPROVED)
    if approved > 0:
        return ST_COMPLETED
    return ST_IN_PROGRESS


def _visa_and_admitted_states(_student_file) -> tuple[str, str, str]:
    return (ST_UPCOMING, ST_UPCOMING, ST_UPCOMING)


def compute_raw_progress_states(student_file) -> list[str]:
    raw_states = [
        ST_COMPLETED,
        _payment_step_state(student_file),
        _documents_under_review_state(student_file),
        _documents_verified_state(student_file),
        _university_applied_state(student_file),
    ]
    visa_applied, visa_approved, admitted = _visa_and_admitted_states(student_file)
    raw_states.extend([visa_applied, visa_approved, admitted])
    return raw_states


def apply_gating(raw_states: list[str]) -> list[str]:
    gated_states: list[str] = []
    for index, raw in enumerate(raw_states):
        if index == 0:
            gated_states.append(ST_COMPLETED)
            continue
        prior_all_completed = all(raw_states[j] == ST_COMPLETED for j in range(0, index))
        gated_states.append(raw if prior_all_completed else ST_UPCOMING)
    return gated_states


def sync_application_progress(student_file):
    """
    Create or update ``StudentApplicationProgress`` from domain data.

    Steps with ``*_manual`` True are left unchanged.
    """
    from agency_inventory.models import StudentApplicationProgress

    student_file.refresh_from_db()
    tracker, _created = StudentApplicationProgress.objects.get_or_create(
        student_file=student_file,
        defaults={
            "agency_id": student_file.agency_id,
            "business_id": student_file.business_id,
        },
    )

    raw_states = compute_raw_progress_states(student_file)
    gated_states = apply_gating(raw_states)

    update_fields: list[str] = []
    for index, (_key, _label, state_field, manual_field) in enumerate(STEP_DEFINITIONS):
        if getattr(tracker, manual_field):
            continue
        new_value = gated_states[index]
        if getattr(tracker, state_field) != new_value:
            setattr(tracker, state_field, new_value)
            update_fields.append(state_field)

    if tracker.agency_id != student_file.agency_id:
        tracker.agency_id = student_file.agency_id
        update_fields.append("agency")
    if tracker.business_id != student_file.business_id:
        tracker.business_id = student_file.business_id
        update_fields.append("business")

    if update_fields:
        tracker.save(update_fields=list(set(update_fields)))
    return tracker


def serialize_application_progress(student_file) -> dict[str, Any]:
    tracker = sync_application_progress(student_file)
    steps_payload: list[dict[str, Any]] = []
    for order, (api_key, label, state_field, manual_field) in enumerate(STEP_DEFINITIONS, start=1):
        steps_payload.append(
            {
                "key": api_key,
                "label": label,
                "order": order,
                "state": getattr(tracker, state_field),
                "manual": getattr(tracker, manual_field),
            }
        )

    return {
        "student_file_id": student_file.student_file_id,
        "slug": student_file.slug,
        "current_status": student_file.current_status,
        "current_status_label": student_file.get_current_status_display()
        if hasattr(student_file, "get_current_status_display")
        else student_file.current_status,
        "steps": steps_payload,
    }


def parse_admin_progress_payload(raw: Any) -> dict[str, Any]:
    """
    Normalize PATCH body: ``{ "payment_verified": "completed" }`` or
    ``{ "visa_applied": { "state": "in_progress", "manual": true } }``.
    """
    if not isinstance(raw, dict):
        raise ValueError("Request body must be a JSON object keyed by step name.")
    normalized: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in STEP_KEYS:
            raise ValueError(f"Unknown step key: {key!r}. Valid keys: {', '.join(STEP_KEYS)}.")
        if isinstance(value, str):
            normalized[key] = {"state": value, "manual": True}
        elif isinstance(value, dict):
            if "state" not in value:
                raise ValueError(f"Step {key!r} object form requires a 'state' field.")
            normalized[key] = {"state": value["state"], "manual": value.get("manual", True)}
        else:
            raise ValueError(f"Invalid value for step {key!r}: use a string state or an object.")
    if not normalized:
        raise ValueError("Provide at least one step key to update.")
    return normalized


def apply_admin_progress_patch(student_file, validated_steps: dict[str, Any]):
    """
    Apply admin-provided step updates. Each provided step sets ``*_manual`` True
    unless ``manual`` is explicitly False (unlocks the step for auto sync again).
    """
    from agency_inventory.models import StudentApplicationProgress

    tracker = StudentApplicationProgress.objects.filter(student_file=student_file).first()
    if tracker is None:
        tracker = sync_application_progress(student_file)

    update_fields: list[str] = []
    key_to_spec = {row[0]: row for row in STEP_DEFINITIONS}

    for payload_key, payload_value in validated_steps.items():
        if payload_key not in key_to_spec:
            continue
        _api_key, _label, state_field, manual_field = key_to_spec[payload_key]
        state_value = payload_value["state"]
        manual_value = payload_value.get("manual", True)

        allowed_states = {choice for choice, _label in ApplicationProgressStepState.choices}
        if state_value not in allowed_states:
            raise ValueError(f"Invalid state for {payload_key}: {state_value!r}")

        setattr(tracker, state_field, state_value)
        setattr(tracker, manual_field, bool(manual_value))
        update_fields.extend([state_field, manual_field])

    if update_fields:
        tracker.save(update_fields=list(set(update_fields)))
    # Re-run auto sync so unlocked steps stay aligned with invoices / docs / applications.
    return sync_application_progress(student_file)
