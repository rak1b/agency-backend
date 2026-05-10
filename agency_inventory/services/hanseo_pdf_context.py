"""
Build template context for the Hanseo university PDF pack (WeasyPrint).

Student education/family rows and the optional ``translator_profile`` JSON blob
are normalized into display strings for the HTML template.
"""

from __future__ import annotations

import base64
import calendar
import mimetypes
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils.safestring import mark_safe

from agency_inventory.constants import AcademicDegreeChoice, GenderChoice
from agency_inventory.models import StudentFile


def _hanseo_asset_data_uri(filename: str) -> str:
    """Load a bundled Hanseo asset from ``templates/images/hanseo`` as a data URI."""
    path = Path(settings.BASE_DIR) / "templates" / "images" / "hanseo" / filename
    if not path.is_file():
        return ""
    raw = path.read_bytes()
    mime, _ = mimetypes.guess_type(path.name)
    if not mime:
        ext = path.suffix.lower()
        if ext in (".jpg", ".jpeg"):
            mime = "image/jpeg"
        elif ext == ".png":
            mime = "image/png"
        else:
            mime = "application/octet-stream"
    encoded = base64.b64encode(raw).decode("ascii")
    return mark_safe(f"data:{mime};base64,{encoded}")


def _remote_url_to_data_uri(url: str, *, timeout: int = 20) -> str:
    """Fetch an http(s) image URL and return a data URI for embedding in PDF."""
    if not url or not isinstance(url, str):
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return ""
    try:
        req = Request(url, headers={"User-Agent": "Agency-backend/1.0 (Hanseo PDF)"})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        content_type = resp.headers.get_content_type() if hasattr(resp.headers, "get_content_type") else None
        mime = content_type or mimetypes.guess_type(url)[0] or "application/octet-stream"
        encoded = base64.b64encode(raw).decode("ascii")
        return mark_safe(f"data:{mime};base64,{encoded}")
    except (URLError, OSError, ValueError):
        return ""


def _split_date_string(value: str | None) -> tuple[str, str, str]:
    """Return (yyyy, mm, dd) strings from YYYY-MM-DD / similar; blanks if unparsable."""
    if not value or not isinstance(value, str):
        return "", "", ""
    cleaned = value.strip().replace("/", "-").replace(".", "-")
    parts = [p for p in cleaned.split("-") if p]
    if len(parts) >= 3:
        y, m, d = parts[0], parts[1].zfill(2), parts[2].zfill(2)
        if y.isdigit() and m.isdigit() and d.isdigit():
            return y, m, d
    return "", "", ""


def _format_dob_banner(d: date) -> str:
    """Example: 2004 DEC 15 (matches the legacy static Hanseo layout; plain spaces + nowrap CSS)."""
    mon = calendar.month_abbr[d.month].upper()
    return f"{d.year} {mon} {d.day:02d}"


def _gender_label(gender_value: str) -> str:
    if gender_value == GenderChoice.MALE:
        return "MALE"
    if gender_value == GenderChoice.FEMALE:
        return "FEMALE"
    return "OTHER"


def _academic_degree_display(value: str) -> str:
    """Human-readable degree for PDF; unknown / legacy strings pass through."""
    raw = (value or "").strip()
    if not raw:
        return ""
    for choice_val, choice_label in AcademicDegreeChoice.choices:
        if raw == choice_val:
            return str(choice_label)
    return raw


# Hanseo Application of Admission groups stored degrees into three lines:
#   Elementary School ← SSC, College ← HSC, University ← BACHELOR (+ MASTERS).
HANSEO_ELEMENTARY_LABEL = "Elementary School"
HANSEO_COLLEGE_LABEL = "College"
HANSEO_UNIVERSITY_LABEL = "University"


def _empty_education_row(label: str) -> dict[str, str]:
    return {
        "degree": label,
        "institution": "",
        "study_period": "",
        "result": "",
        "graduation_date": "",
        "institution_phone": "",
        "admission_date": "",
    }


def _education_row_payload(label: str, src) -> dict[str, str]:
    """Project a ``StudentEducationBackground`` row onto the Hanseo template shape."""
    if src is None:
        return _empty_education_row(label)
    return {
        "degree": label,
        "institution": src.institution or "",
        "study_period": src.study_period or "",
        "result": src.result or "",
        "graduation_date": src.graduation_date.isoformat() if src.graduation_date else "",
        "institution_phone": src.institution_phone or "",
        "admission_date": src.admission_date.isoformat() if src.admission_date else "",
    }


def _hanseo_education_rows(sf: StudentFile) -> list[dict[str, str]]:
    """
    Build the Hanseo-style academic background rows:
        Elementary School  ← stored SSC row
        College            ← stored HSC row
        University         ← stored BACHELOR row (+ a second University row for MASTERS,
                              when both are present).

    A single "University" row is rendered when only one of BACHELOR / MASTERS exists
    (or as an empty placeholder when neither is provided). PhD rows are intentionally
    not surfaced on this admission form.
    """
    by_degree: dict[str, list] = {}
    for row in sf.education_background_rows.all():
        by_degree.setdefault(str(row.degree), []).append(row)

    def _first(degree_value: str):
        bucket = by_degree.get(degree_value) or []
        return bucket[0] if bucket else None

    ssc = _first(str(AcademicDegreeChoice.SSC))
    hsc = _first(str(AcademicDegreeChoice.HSC))
    bachelor = _first(str(AcademicDegreeChoice.BACHELOR))
    masters = _first(str(AcademicDegreeChoice.MASTERS))

    rows: list[dict[str, str]] = [
        _education_row_payload(HANSEO_ELEMENTARY_LABEL, ssc),
        _education_row_payload(HANSEO_COLLEGE_LABEL, hsc),
    ]
    if bachelor and masters:
        rows.append(_education_row_payload(HANSEO_UNIVERSITY_LABEL, bachelor))
        rows.append(_education_row_payload(HANSEO_UNIVERSITY_LABEL, masters))
    elif bachelor:
        rows.append(_education_row_payload(HANSEO_UNIVERSITY_LABEL, bachelor))
    elif masters:
        rows.append(_education_row_payload(HANSEO_UNIVERSITY_LABEL, masters))
    else:
        rows.append(_empty_education_row(HANSEO_UNIVERSITY_LABEL))
    return rows


def _pick_college_row(rows: list[dict[str, str]]) -> dict[str, str]:
    """
    Pick the row used for the page-2 / page-3 agreement (school name + dates).

    Priority: filled "College" (HSC) → filled "University" (Bachelor/Masters) →
    filled "Elementary School" (SSC) → first row carrying any institution → fallback.
    """
    if not rows:
        return {}

    def _has_institution(row: dict[str, str]) -> bool:
        return bool((row.get("institution") or "").strip())

    label_priority = (HANSEO_COLLEGE_LABEL, HANSEO_UNIVERSITY_LABEL, HANSEO_ELEMENTARY_LABEL)
    for label in label_priority:
        for row in rows:
            if row.get("degree") == label and _has_institution(row):
                return row
    for row in rows:
        if _has_institution(row):
            return row
    for label in label_priority:
        for row in rows:
            if row.get("degree") == label:
                return row
    return rows[0]


def _study_period_years(study_period: str) -> tuple[str, str]:
    if not study_period:
        return "", ""
    m = re.search(r"(\d{4})\s*[-–]\s*(\d{4})", study_period)
    if m:
        return m.group(1), m.group(2)
    return "", ""


def _default_family_template() -> list[dict[str, str]]:
    return [
        {"relation": "FATHER", "name": "", "date_of_birth": "", "occupation": "", "monthly_income": "", "workplace": "", "workplace_phone": ""},
        {"relation": "MOTHER", "name": "", "date_of_birth": "", "occupation": "", "monthly_income": "", "workplace": "", "workplace_phone": ""},
        {"relation": "", "name": "", "date_of_birth": "", "occupation": "", "monthly_income": "", "workplace": "", "workplace_phone": ""},
    ]


def _merge_family_rows(sf: StudentFile, stored: list[Any] | None) -> list[dict[str, str]]:
    defaults = _default_family_template()
    rows = list(stored or [])
    if not rows and (sf.father_name or sf.mother_name):
        rows = [
            {
                "relation": "FATHER",
                "name": sf.father_name or "",
                "date_of_birth": "",
                "occupation": "",
                "monthly_income": "",
                "workplace": "",
                "workplace_phone": "",
            },
            {
                "relation": "MOTHER",
                "name": sf.mother_name or "",
                "date_of_birth": "",
                "occupation": "",
                "monthly_income": "",
                "workplace": "",
                "workplace_phone": "",
            },
        ]
    merged: list[dict[str, str]] = []
    for i, slot in enumerate(defaults):
        src = rows[i] if i < len(rows) and isinstance(rows[i], dict) else {}
        merged.append(
            {
                "relation": str(src.get("relation") or slot["relation"]),
                "name": str(src.get("name") or ""),
                "date_of_birth": str(src.get("date_of_birth") or ""),
                "occupation": str(src.get("occupation") or ""),
                "monthly_income": str(src.get("monthly_income") or ""),
                "workplace": str(src.get("workplace") or ""),
                "workplace_phone": str(src.get("workplace_phone") or ""),
            }
        )
    return merged


def _student_family_rows(sf: StudentFile) -> list[dict[str, str]]:
    return [
        {
            "relation": row.relation,
            "name": row.name,
            "date_of_birth": row.date_of_birth.isoformat() if row.date_of_birth else "",
            "occupation": row.occupation,
            "monthly_income": row.monthly_income,
            "workplace": row.workplace,
            "workplace_phone": row.workplace_phone,
        }
        for row in sf.family_particular_rows.all()
    ]


def build_hanseo_template_context(
    student_file: StudentFile,
    *,
    form_date: date | None = None,
    fallback_passport_asset: str = "bablu_passport.jpeg",
) -> dict[str, Any]:
    """
    Map a ``StudentFile`` into the variables expected by ``hanseo.html``.

    ``form_date`` defaults to today (local) and drives title / signature dates.
    """
    sf = student_file
    today = form_date or date.today()

    dob = sf.date_of_birth
    dob_y, dob_m, dob_d = str(dob.year), f"{dob.month:02d}", f"{dob.day:02d}"

    given_line = " ".join(p for p in (sf.given_name, (sf.middle_name or "").strip()) if p).strip()
    full_name_caps = f"{sf.surname} {sf.given_name}".strip().upper()
    if sf.middle_name:
        full_name_caps = f"{sf.surname} {sf.given_name} {sf.middle_name.strip()}".strip().upper()

    gender_val: str = str(sf.gender or GenderChoice.OTHER)
    gender_label = _gender_label(gender_val)
    gender_is_male = gender_val == GenderChoice.MALE
    gender_is_female = gender_val == GenderChoice.FEMALE

    education_rows = _hanseo_education_rows(sf)
    college = _pick_college_row(education_rows)
    admit_y, admit_m, admit_d = _split_date_string(college.get("admission_date"))
    grad_y, grad_m, grad_d = _split_date_string(college.get("graduation_date"))
    span_from, span_to = _study_period_years(college.get("study_period", ""))
    if not admit_y and span_from:
        admit_y = span_from
    if not grad_y and span_to:
        grad_y = span_to

    family_rows = _merge_family_rows(sf, _student_family_rows(sf))

    translator = sf.translator_profile if isinstance(sf.translator_profile, dict) else {}
    tr_gender = (translator.get("gender") or "").upper()
    tr_is_male = tr_gender in ("M", "MALE", GenderChoice.MALE)
    tr_is_female = tr_gender in ("F", "FEMALE", GenderChoice.FEMALE)

    passport_uri = _remote_url_to_data_uri(sf.passport_photo_url or "")
    if not passport_uri:
        passport_uri = _hanseo_asset_data_uri(fallback_passport_asset)

    default_statement = (
        "I am applying for admission at the institute of Language and Culture Education."
    )
    statement = (sf.application_statement or "").strip() or default_statement

    translated_note = (sf.translated_documents_note or "").strip() or "—"

    title_date = today.strftime("%Y-%m-%d")
    form_title = f"{title_date} Application of Admission"

    return {
        "form_title": form_title,
        "student_file_id": sf.student_file_id or "",
        "surname": sf.surname,
        "given_name": sf.given_name,
        "given_name_line": given_line,
        "full_name_caps": full_name_caps,
        "dob_display": _format_dob_banner(dob),
        "dob_iso": dob.isoformat(),
        "dob_y": dob_y,
        "dob_m": dob_m,
        "dob_d": dob_d,
        "nationality": (sf.nationality or "").upper() or "—",
        "place_of_birth": (sf.place_of_birth or "").upper() or "—",
        "gender_label": gender_label,
        "gender_is_male": gender_is_male,
        "gender_is_female": gender_is_female,
        "present_address": sf.present_address or "—",
        "permanent_address": sf.permanent_address or "—",
        "phone_whatsapp": sf.phone_whatsapp or "—",
        "email": sf.email or "—",
        "education_rows": education_rows,
        "family_rows": family_rows,
        "application_statement": statement,
        "statement_date": today.strftime("%Y/%m/%d"),
        "agreement_school_name": college.get("institution") or "—",
        "agreement_from_year": span_from or admit_y or "—",
        "agreement_to_year": span_to or grad_y or "—",
        "agreement_admit_y": admit_y or "",
        "agreement_admit_m": admit_m or "",
        "agreement_admit_d": admit_d or "",
        "agreement_grad_y": grad_y or "",
        "agreement_grad_m": grad_m or "",
        "agreement_grad_d": grad_d or "",
        "agreement_full_name": full_name_caps,
        "agreement_date_y": str(today.year),
        "agreement_date_m": f"{today.month:02d}",
        "agreement_date_d": f"{today.day:02d}",
        "highest_education_postal_code": sf.highest_education_postal_code or "",
        "highest_education_address": sf.highest_education_address or "",
        "highest_education_fax": sf.highest_education_fax or "",
        "highest_education_website": sf.highest_education_website or "",
        "translator_nationality": (translator.get("nationality") or "").upper() or "—",
        "translator_name": translator.get("name") or "—",
        "translator_dob_display": translator.get("date_of_birth") or "—",
        "translator_gender_male": tr_is_male,
        "translator_gender_female": tr_is_female,
        "translator_address": translator.get("address") or "—",
        "translator_home_phone": translator.get("home_phone") or "",
        "translator_mobile": translator.get("mobile") or "",
        "owner_nationality": (sf.nationality or "").upper() or "—",
        "owner_name_display": full_name_caps,
        "owner_dob_paren": f"({dob.isoformat()})",
        "translated_documents_note": translated_note,
        "p4_sign_date_y": str(today.year),
        "p4_sign_date_m": f"{today.month:02d}",
        "p4_sign_date_d": f"{today.day:02d}",
        "p2_date_y": str(today.year),
        "p2_date_m": f"{today.month:02d}",
        "p2_date_d": f"{today.day:02d}",
        "passport_number": sf.passport_number or "",
        "hanseo_passport_uri": passport_uri,
        "hanseo_logo_uri": _hanseo_asset_data_uri("logo.png"),
        "hanseo_sign_uri": _hanseo_asset_data_uri("dummy_sign.jpg"),
    }


def scoped_student_files_queryset(request):
    """
    Same visibility as ``StudentFileViewSet`` for non-list access: business tenant,
    B2B agency stamp, student portal linked file only.
    """
    from authentication.tenant_utils import (
        apply_b2b_agency_scope_to_queryset,
        is_student_portal_user,
        tenant_business_id,
        user_is_master_admin,
    )

    user = getattr(request, "user", None)
    qs = StudentFile.objects.select_related("agency", "business", "created_by").all()
    if not user or not user.is_authenticated:
        return StudentFile.objects.none()
    if user_is_master_admin(user):
        scoped = qs
    else:
        business_id = tenant_business_id(user)
        if not business_id:
            return StudentFile.objects.none()
        scoped = qs.filter(business_id=business_id)
    scoped = apply_b2b_agency_scope_to_queryset(scoped, user)
    if is_student_portal_user(user):
        linked = getattr(user, "linked_student_file_id", None)
        if linked:
            return scoped.filter(pk=linked)
        return StudentFile.objects.none()
    return scoped
