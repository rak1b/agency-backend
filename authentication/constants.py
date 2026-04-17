from django.db.models import IntegerChoices, TextChoices
from django.utils.translation import gettext_lazy as _

class GenderChoice(IntegerChoices):
    MALE = 0, _("Male")
    FEMALE = 1, _("Female")
    OTHER = 2, _("Other")


MALE = GenderChoice.MALE
FEMALE = GenderChoice.FEMALE
OTHER = GenderChoice.OTHER
GENDER_OPTIONS = GenderChoice.choices


class UserTypeChoice(TextChoices):
    AGENCY_SUPER_ADMIN = "AGENCY_SUPER_ADMIN", _("Agency Super Admin")
    AGENCY_EMPLOYEE = "AGENCY_EMPLOYEE", _("Agency Employee")
    B2B_AGENT = "B2B_AGENT", _("B2B Agent")
    B2B_AGENT_EMPLOYEE = "B2B_AGENT_EMPLOYEE", _("B2B Agent Employee")


USER_TYPE_OPTIONS = UserTypeChoice.choices


# Role Options
ADMIN = 0
MERCHANT = 1

ROLE_OPTIONS = (
    (ADMIN, _("Admin")),
    (MERCHANT, _("Merchant")),
)