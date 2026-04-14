from django.db import models

from authentication.base import BaseModel
from utils.slug_utils import generate_unique_code, generate_unique_slug
from .constants import (
    AgencyStatusChoice,
    CustomerStatusChoice,
    FileFromChoice,
    GenderChoice,
    UniversityProgramChoice,
)


class Agency(BaseModel):
    """
    Core agency profile used by the student-management workflow.
    """

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    owner_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=AgencyStatusChoice.choices, default=AgencyStatusChoice.PENDING)
    contract_start_date = models.DateField()
    contract_end_date = models.DateField()
    business_email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30)
    address = models.TextField()
    logo_image_url = models.URLField(max_length=1000, blank=True, null=True)
    trade_license_image_url = models.URLField(max_length=1000, blank=True, null=True)
    created_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = generate_unique_slug(self.name, self)
        super().save(*args, **kwargs)


class Customer(BaseModel):
    """
    Student/customer file profile linked to an agency.
    """

    customer_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="customers")
    passport_number = models.CharField(max_length=100, unique=True)
    passport_copy_url = models.URLField(max_length=1000, blank=True, null=True)
    surname = models.CharField(max_length=100)
    given_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    phone_whatsapp = models.CharField(max_length=30)
    facebook_id_link = models.URLField(max_length=1000, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    date_of_birth = models.DateField()
    father_name = models.CharField(max_length=150)
    mother_name = models.CharField(max_length=150)
    gender = models.CharField(max_length=20, choices=GenderChoice.choices, default=GenderChoice.OTHER)
    current_status = models.CharField(
        max_length=20,
        choices=CustomerStatusChoice.choices,
        default=CustomerStatusChoice.FILE_RECEIVED,
    )
    file_from = models.CharField(max_length=20, choices=FileFromChoice.choices, default=FileFromChoice.AGENCY_OWN)
    assigned_counselor = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_customers",
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer_id or 'CUSTOMER'} - {self.given_name} {self.surname}".strip()

    def save(self, *args, **kwargs):
        if not self.customer_id:
            self.customer_id = generate_unique_code(Customer, field_name="customer_id", prefix="CUS", number_length=8)
        if not self.slug:
            slug_source = f"{self.given_name}-{self.surname}-{self.passport_number}"
            self.slug = generate_unique_slug(slug_source, self)
        super().save(*args, **kwargs)


class University(BaseModel):
    """
    University base profile grouped by country.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    country = models.CharField(max_length=120)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["name", "country"], name="unique_university_name_country"),
        ]

    def __str__(self):
        return f"{self.name} ({self.country})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(f"{self.name}-{self.country}", self)
        super().save(*args, **kwargs)


class UniversityIntake(BaseModel):
    """
    Intake periods available under a university (e.g. June, March, September).
    """

    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="intakes")
    intake_name = models.CharField(max_length=50)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["university", "intake_name"], name="unique_intake_per_university"),
        ]

    def __str__(self):
        return f"{self.university.name} - {self.intake_name}"


class UniversityProgram(BaseModel):
    """
    Program options enabled for a university.
    """

    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="programs")
    program = models.CharField(max_length=20, choices=UniversityProgramChoice.choices)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["university", "program"], name="unique_program_per_university"),
        ]

    def __str__(self):
        return f"{self.university.name} - {self.program}"


class OfficeCost(BaseModel):
    """
    Office-level operational cost entry.
    """

    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="office_costs")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    amount = models.PositiveIntegerField(default=0)
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    created_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.amount})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(f"{self.title}-{self.agency_id}", self)
        super().save(*args, **kwargs)


class StudentCost(BaseModel):
    """
    Customer/student specific cost entry.
    """

    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="student_costs")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="costs")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    amount = models.PositiveIntegerField(default=0)
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    created_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.given_name} - {self.title} ({self.amount})"

    def save(self, *args, **kwargs):
        if self.customer and self.agency_id != self.customer.agency_id:
            self.agency = self.customer.agency
        if not self.slug:
            self.slug = generate_unique_slug(f"{self.title}-{self.customer_id}", self)
        super().save(*args, **kwargs)