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
    ("dhl_sent_to_university", "DHL Sent to University", "dhl_sent_to_university", "dhl_sent_to_university_manual"),
    ("dhl_received_from_university", "DHL Received from University", "dhl_received_from_university", "dhl_received_from_university_manual"),
    ("interview_scheduled", "Interview Scheduled", "interview_scheduled", "interview_scheduled_manual"),
    ("interview_completed", "Interview Completed", "interview_completed", "interview_completed_manual"),
    ("admission_letter_received", "Admission Letter Received", "admission_letter_received", "admission_letter_received_manual"),
    ("tuition_fee_paid", "Tuition Fee Paid", "tuition_fee_paid", "tuition_fee_paid_manual"),
    ("visa_applied", "Visa Applied", "visa_applied", "visa_applied_manual"),
    ("visa_approved", "Visa Approved", "visa_approved", "visa_approved_manual"),
    ("visa_rejected", "Visa Rejected", "visa_rejected", "visa_rejected_manual"),
    ("visa_received", "Visa Received", "visa_received", "visa_received_manual"),
    ("admitted", "Admitted", "admitted", "admitted_manual"),
    ("enrolled", "Enrolled", "enrolled", "enrolled_manual"),
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


def _visa_applied_approved_and_admitted_states(_student_file) -> tuple[str, str, str]:
    """Placeholder until visa / admission signals are wired to domain models."""
    return (ST_UPCOMING, ST_UPCOMING, ST_UPCOMING)


def compute_raw_progress_states(student_file) -> list[str]:
    """
    One raw state per ``STEP_DEFINITIONS`` row (before linear gating).

    Steps without dedicated domain rules stay ``upcoming`` until you add
    helpers (invoices, logistics, interviews, etc.) and plug them in here.
    """
    head: list[str] = [
        ST_COMPLETED,
        _payment_step_state(student_file),
        _documents_under_review_state(student_file),
        _documents_verified_state(student_file),
        _university_applied_state(student_file),
    ]
    middle: list[str] = [ST_UPCOMING] * 6
    visa_applied_s, visa_approved_s, admitted_s = _visa_applied_approved_and_admitted_states(student_file)
    tail: list[str] = [
        visa_applied_s,
        visa_approved_s,
        ST_UPCOMING,
        ST_UPCOMING,
        admitted_s,
        ST_UPCOMING,
    ]
    raw_states = head + middle + tail
    expected = len(STEP_DEFINITIONS)
    if len(raw_states) != expected:
        raise RuntimeError(f"raw state count {len(raw_states)} must match STEP_DEFINITIONS ({expected}).")
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


def _expand_patch_with_completed_prior_steps(
    validated_steps: dict[str, Any],
) -> dict[str, Any]:
    """
    If a step is moved to ``completed`` or ``in_progress``, all earlier steps in
    the ordered pipeline should be ``completed`` for a coherent timeline.

    Keys already present in ``validated_steps`` keep their explicit payload (so
    staff can intentionally diverge). Steps implied only by this rule inherit
    ``manual`` from the step that triggered the cascade.
    """
    merged: dict[str, Any] = dict(validated_steps)
    for payload_key, payload_value in validated_steps.items():
        state_value = payload_value["state"]
        if state_value not in (ST_COMPLETED, ST_IN_PROGRESS):
            continue
        step_index = STEP_KEYS.index(payload_key)
        manual_value = payload_value.get("manual", True)
        for prior_index in range(step_index):
            prior_key = STEP_KEYS[prior_index]
            if prior_key not in validated_steps:
                merged[prior_key] = {
                    "state": ST_COMPLETED,
                    "manual": bool(manual_value),
                }
    return merged


def apply_admin_progress_patch(student_file, validated_steps: dict[str, Any]):
    """
    Apply admin-provided step updates. Each provided step sets ``*_manual`` True
    unless ``manual`` is explicitly False (unlocks the step for auto sync again).

    When a step is set to ``completed`` or ``in_progress``, every earlier step in
    the pipeline is also set to ``completed`` (unless that step was included in
    the same request); implied steps share the triggering step's ``manual`` flag.
    """
    from agency_inventory.models import StudentApplicationProgress

    tracker = StudentApplicationProgress.objects.filter(student_file=student_file).first()
    if tracker is None:
        tracker = sync_application_progress(student_file)

    update_fields: list[str] = []
    key_to_spec = {row[0]: row for row in STEP_DEFINITIONS}

    merged_steps = _expand_patch_with_completed_prior_steps(validated_steps)

    for payload_key, payload_value in merged_steps.items():
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
