from django.db import models
from django.utils.translation import gettext_lazy as _


class AgencyStatusChoice(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    ACTIVE = "ACTIVE", _("Active")
    SUSPENDED = "SUSPENDED", _("Suspended")
    CLOSED = "CLOSED", _("Closed")


class CustomerStatusChoice(models.TextChoices):
    FILE_RECEIVED = "FILE_RECEIVED", _("File Received")
    PROCESSING = "PROCESSING", _("Processing")
    APPLIED = "APPLIED", _("Applied")
    ENROLLED = "ENROLLED", _("Enrolled")
    REJECTED = "REJECTED", _("Rejected")


class FileFromChoice(models.TextChoices):
    AGENCY_OWN = "AGENCY_OWN", _("Agency's own")
    SUB_AGENT = "SUB_AGENT", _("Sub agent")
    DIRECT = "DIRECT", _("Direct")


class GenderChoice(models.TextChoices):
    MALE = "MALE", _("Male")
    FEMALE = "FEMALE", _("Female")
    OTHER = "OTHER", _("Other")


class UniversityProgramChoice(models.TextChoices):
    EAP = "EAP", _("EAP")
    KLP = "KLP", _("KLP")
    DIPLOMA = "DIPLOMA", _("Diploma")
    BACHELOR = "BACHELOR", _("Bachelor")
    MASTER = "MASTER", _("Master's")
    PHD = "PHD", _("PhD")