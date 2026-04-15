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
    EAP = "EAP", _("EAP")
    KLP = "KLP", _("KLP")
    DIPLOMA = "DIPLOMA", _("Diploma")
    BACHELOR = "BACHELOR", _("Bachelor")
    MASTER = "MASTER", _("Master's")
    PHD = "PHD", _("PhD")