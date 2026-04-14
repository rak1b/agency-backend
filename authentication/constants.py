from django.db.models import IntegerChoices
from django.utils.translation import gettext_lazy as _

# Gender Options
MALE = 0
FEMALE = 1
OTHER = 2

GENDER_OPTIONS = {
    (MALE, _("Male")),
    (FEMALE, _("Female")),
    (OTHER, _("Other")),
}


# Role Options
ADMIN = 0
MERCHANT = 1

ROLE_OPTIONS = {
    (ADMIN, _("Admin")),
    (MERCHANT, _("Merchant")),
}