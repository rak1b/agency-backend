from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class AgencyStatusChoice(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    ACTIVE = "ACTIVE", _("Active")
    SUSPENDED = "SUSPENDED", _("Suspended")
    CLOSED = "CLOSED", _("Closed")


class CustomerStatusChoice(models.TextChoices):
    FILE_RECEIVED = "FILE_RECEIVED", _("File Received")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    FILE_OPENED = "FILE_OPENED", _("File Opened")


class FileFromChoice(models.TextChoices):
    AGENCY_OWN = "AGENCY_OWN", _("Agency's own")
    SUB_AGENT = "SUB_AGENT", _("Sub agent")
    DIRECT = "DIRECT", _("Direct")


class GenderChoice(models.TextChoices):
    MALE = "MALE", _("Male")
    FEMALE = "FEMALE", _("Female")
    OTHER = "OTHER", _("Other")


class UniversityProgramChoice(models.TextChoices):
    """
    Stored values align with typical frontend ``PROGRAM_LEVELS`` ids (EAP, KLP, DIPLOMA,
    BACHELOR, MASTERS, PHD). Use :func:`normalize_university_program_input` to accept
    labels (e.g. ``Bachelor``) and legacy ``MASTER``.
    """

    EAP = "EAP", _("EAP")
    KLP = "KLP", _("KLP")
    DIPLOMA = "DIPLOMA", _("Diploma")
    BACHELOR = "BACHELOR", _("Bachelor")
    MASTERS = "MASTERS", _("Master's")
    PHD = "PHD", _("PhD")


_UNIVERSITY_PROGRAM_VALID_VALUES = frozenset(
    (
        UniversityProgramChoice.EAP,
        UniversityProgramChoice.KLP,
        UniversityProgramChoice.DIPLOMA,
        UniversityProgramChoice.BACHELOR,
        UniversityProgramChoice.MASTERS,
        UniversityProgramChoice.PHD,
    )
)

# Lowercase aliases (labels, typos, legacy codes) -> stored value
_UNIVERSITY_PROGRAM_ALIASES_TO_VALUE = {
    "eap": "EAP",
    "klp": "KLP",
    "diploma": "DIPLOMA",
    "bachelor": "BACHELOR",
    "bachelor's": "BACHELOR",
    "bachelors": "BACHELOR",
    "master": "MASTERS",
    "master's": "MASTERS",
    "masters": "MASTERS",
    "msc": "MASTERS",
    "phd": "PHD",
    "doctorate": "PHD",
}


def normalize_university_program_input(raw) -> str:
    """
    Return a canonical ``UniversityProgramChoice`` value string.

    Accepts stored codes (``BACHELOR``), frontend ids (``MASTERS``), display labels
    (``Bachelor``, ``Master's``), and legacy ``MASTER``.
    """
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise ValidationError("This field may not be blank.")
    value = str(raw).strip()
    if value in _UNIVERSITY_PROGRAM_VALID_VALUES:
        return value
    mapped = _UNIVERSITY_PROGRAM_ALIASES_TO_VALUE.get(value.lower())
    if mapped:
        return mapped
    raise ValidationError(f"{raw!r} is not a valid program level.")