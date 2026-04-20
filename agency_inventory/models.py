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
    trade_license_no = models.CharField(max_length=100, blank=True, null=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

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


class StudentFile(BaseModel):
    """
    Dedicated student file entity aligned with the student-file creation form.
    """

    student_file_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, related_name="student_files", null=True, blank=True)
    is_own_agency = models.BooleanField(default=False)
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
    attachments = models.ManyToManyField(
        "StudentFileAttachment",
        related_name="student_files",
        blank=True,
    )
    applied_universities = models.ManyToManyField(
        "AppliedUniversity",
        related_name="student_files",
        blank=True,
    )
    current_status = models.CharField(
        max_length=20,
        choices=CustomerStatusChoice.choices,
        default=CustomerStatusChoice.FILE_RECEIVED,
    )
    file_from = models.CharField(max_length=20, choices=FileFromChoice.choices, default=FileFromChoice.AGENCY_OWN)
    created_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student_file_id or 'STUDENT_FILE'} - {self.given_name} {self.surname}".strip()

    def save(self, *args, **kwargs):
        if not self.student_file_id:
            self.student_file_id = generate_unique_code(StudentFile, field_name="student_file_id", prefix="STF", number_length=8)
        if not self.slug:
            slug_source = f"{self.given_name}-{self.surname}-{self.passport_number}"
            self.slug = generate_unique_slug(slug_source, self)
        super().save(*args, **kwargs)


class AppliedUniversity(BaseModel):
    """
    Optional applied-university records linked to student files.
    """

    university = models.ForeignKey(
        "University",
        on_delete=models.SET_NULL,
        related_name="applied_universities",
        null=True,
        blank=True,
    )
    country = models.ForeignKey(
        "Country",
        on_delete=models.SET_NULL,
        related_name="applied_universities",
        null=True,
        blank=True,
    )
    intake = models.CharField(max_length=100, blank=True, null=True)
    subject = models.ForeignKey(
        "UniversityProgramSubject",
        on_delete=models.SET_NULL,
        related_name="applied_universities",
        null=True,
        blank=True,
    )
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        university_name = self.university.university_name if self.university else "Applied university"
        if self.intake:
            return f"{university_name} - {self.intake}"
        return university_name

    def save(self, *args, **kwargs):
        # Keep country aligned with selected university to avoid data mismatch.
        if self.university_id:
            resolved_country = self.university.country
            if isinstance(resolved_country, University):
                # Defensive fallback for unexpected legacy/corrupt relation values.
                resolved_country = resolved_country.country
            self.country = resolved_country
        elif isinstance(self.country, University):
            # Defensive fallback for unexpected legacy/corrupt relation values.
            self.country = self.country.country
        if not self.slug:
            slug_source = (
                self.university.university_name
                if self.university_id
                else self.intake or "applied-university"
            )
            self.slug = generate_unique_slug(slug_source, self)
        super().save(*args, **kwargs)


class StudentFileAttachment(BaseModel):
    """
    Attachment metadata for student files (title + uploaded file URL).
    """

    title = models.CharField(max_length=255, blank=True, null=True)
    file_url = models.URLField(max_length=1000, blank=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or "Student attachment"

    def save(self, *args, **kwargs):
        if not self.slug:
            slug_source = self.title or self.file_url or "student-file-attachment"
            self.slug = generate_unique_slug(slug_source, self)
        super().save(*args, **kwargs)


class Country(BaseModel):
    """
    Country master used by universities and applied-university rows.
    """

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self.name, self)
        super().save(*args, **kwargs)


class University(BaseModel):
    """
    University profile (``university_name`` + country). Intakes, enabled programs, and per-program
    subject/track rows are stored on related models and are created together via the
    university API (nested ``intakes`` and ``programs`` payloads).
    """

    university_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="universities")
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["university_name", "country"],
                name="unique_university_name_country",
            ),
        ]

    def __str__(self):
        return f"{self.university_name} ({self.country.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(f"{self.university_name}-{self.country_id}", self)
        super().save(*args, **kwargs)


class UniversityIntake(BaseModel):
    """
    Intake periods available under a university (e.g. June, March, September).
    """

    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="intakes")
    intake_name = models.CharField(max_length=50)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["university", "intake_name"], name="unique_intake_per_university"),
        ]

    def __str__(self):
        return f"{self.university.university_name} - {self.intake_name}"

    def save(self, *args, **kwargs):
        if not self.slug and self.university_id:
            self.slug = generate_unique_slug(f"{self.university_id}-{self.intake_name}", self)
        super().save(*args, **kwargs)


class UniversityProgram(BaseModel):
    """
    Program options enabled for a university.
    """

    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="programs")
    program = models.CharField(max_length=20, choices=UniversityProgramChoice.choices)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["university", "program"], name="unique_program_per_university"),
        ]

    def __str__(self):
        return f"{self.university.university_name} - {self.program}"

    def save(self, *args, **kwargs):
        if not self.slug and self.university_id:
            self.slug = generate_unique_slug(f"{self.university_id}-{self.program}", self)
        super().save(*args, **kwargs)


class UniversityProgramSubject(BaseModel):
    """
    Subject and track rows configured under a university program (e.g. EAP, KLP).
    Matches super-admin "Subjects under program" form sections.
    """

    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    program = models.ForeignKey(UniversityProgram, on_delete=models.CASCADE, related_name="subjects")
    subject_name = models.CharField(max_length=255)
    track_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.program.program} — {self.subject_name}"

    def save(self, *args, **kwargs):
        if not self.slug and self.program_id:
            self.slug = generate_unique_slug(f"{self.program_id}-{self.subject_name}-{self.track_name}", self)
        super().save(*args, **kwargs)


class OfficeCost(BaseModel):
    """
    Office-level operational cost entry.
    """

    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, related_name="office_costs", null=True, blank=True)
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
    Cost entry tied to a student file (not a customer record).
    """

    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, related_name="student_costs", null=True, blank=True)
    student_file = models.ForeignKey(StudentFile, on_delete=models.SET_NULL, related_name="costs", null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    amount = models.PositiveIntegerField(default=0)
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    created_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student_file.given_name} - {self.title} ({self.amount})"

    def save(self, *args, **kwargs):
        if self.student_file_id and self.student_file.agency_id and self.agency_id != self.student_file.agency_id:
            self.agency = self.student_file.agency
        if not self.slug:
            self.slug = generate_unique_slug(f"{self.title}-{self.student_file_id}", self)
        super().save(*args, **kwargs)