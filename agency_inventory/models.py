from django.core.exceptions import ValidationError
from django.db import models

from authentication.base import BaseModel
from utils.slug_utils import generate_unique_code, generate_unique_slug
from .constants import (
    AgencyStatusChoice,
    CustomerStatusChoice,
    FileFromChoice,
    GenderChoice,
)


class Business(BaseModel):
    """
    Top-level tenant. All operational data that belongs to an agency also carries
    ``business_id`` so APIs can isolate rows by business without chaining joins.
    """

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    owner_name = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=AgencyStatusChoice.choices, default=AgencyStatusChoice.ACTIVE)
    business_email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, default="")
    address = models.TextField(blank=True, default="")
    logo_image_url = models.URLField(max_length=1000, blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = generate_unique_slug(self.name, self)
        super().save(*args, **kwargs)


class Agency(BaseModel):
    """
    Core agency profile used by the student-management workflow.
    """

    business = models.ForeignKey(
        Business,
        on_delete=models.PROTECT,
        related_name="agencies",
        null=True,
        blank=True,
    )
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


def _agency_business_pk(agency):
    if agency is None:
        return None
    if isinstance(agency, int):
        return Agency.objects.filter(pk=agency).values_list("business_id", flat=True).first()
    return getattr(agency, "business_id", None)


class Customer(BaseModel):
    """
    Student/customer file profile linked to an agency.
    """

    customer_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="customers")
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="business_customers",
        null=True,
        blank=True,
    )
    passport_number = models.CharField(max_length=100)
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
        if self.business_id is None and self.agency_id:
            self.business_id = _agency_business_pk(self.agency_id)
        super().save(*args, **kwargs)


class StudentFile(BaseModel):
    """
    Dedicated student file entity aligned with the student-file creation form.
    """

    student_file_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    agency = models.ForeignKey(
        Agency,
        on_delete=models.CASCADE,
        related_name="student_files",
        null=True,
        blank=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="business_student_files",
        null=True,
        blank=True,
    )
    is_own_agency = models.BooleanField(default=False)
    passport_number = models.CharField(max_length=100)
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
        if self.business_id is None and self.agency_id:
            self.business_id = _agency_business_pk(self.agency_id)
        super().save(*args, **kwargs)


class AppliedUniversity(BaseModel):
    """
    Optional applied-university records linked to student files.
    """

    agency = models.ForeignKey(
        Agency,
        on_delete=models.CASCADE,
        related_name="agency_applied_universities",
        null=True,
        blank=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="business_applied_universities",
        null=True,
        blank=True,
    )
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
            if self.university.agency_id:
                self.agency_id = self.university.agency_id
        elif isinstance(self.country, University):
            # Defensive fallback for unexpected legacy/corrupt relation values.
            self.country = self.country.country
        if self.country_id and not self.agency_id and getattr(self.country, "agency_id", None):
            self.agency_id = self.country.agency_id
        if not self.slug:
            slug_source = (
                self.university.university_name
                if self.university_id
                else self.intake or "applied-university"
            )
            self.slug = generate_unique_slug(slug_source, self)
        if self.business_id is None:
            if self.university_id and getattr(self.university, "business_id", None):
                self.business_id = self.university.business_id
            elif self.agency_id:
                self.business_id = _agency_business_pk(self.agency_id)
            elif self.country_id and getattr(self.country, "business_id", None):
                self.business_id = self.country.business_id
        super().save(*args, **kwargs)


class StudentFileAttachment(BaseModel):
    """
    Attachment metadata for student files (title + uploaded file URL).
    """

    agency = models.ForeignKey(
        Agency,
        on_delete=models.CASCADE,
        related_name="student_file_attachments",
        null=True,
        blank=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="business_student_file_attachments",
        null=True,
        blank=True,
    )
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
        if self.business_id is None and self.agency_id:
            self.business_id = _agency_business_pk(self.agency_id)
        super().save(*args, **kwargs)


class Country(BaseModel):
    """
    Country catalog scoped to a single agency tenant.
    """

    agency = models.ForeignKey(
        Agency,
        on_delete=models.CASCADE,
        related_name="tenant_countries",
        null=True,
        blank=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="countries",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self.name, self)
        if self.business_id is None and self.agency_id:
            self.business_id = _agency_business_pk(self.agency_id)
        super().save(*args, **kwargs)


class University(BaseModel):
    """
    University profile (``university_name`` + country). Intakes, enabled programs, and per-program
    subject/track rows are stored on related models and are created together via the
    university API (nested ``intakes`` and ``programs`` payloads).
    """

    agency = models.ForeignKey(
        Agency,
        on_delete=models.CASCADE,
        related_name="tenant_universities",
        null=True,
        blank=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="universities",
        null=True,
        blank=True,
    )
    university_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="universities")
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.university_name} ({self.country.name})"



    def save(self, *args, **kwargs):
        if self.country_id and not self.agency_id:
            self.agency_id = self.country.agency_id
        # Do not overwrite an explicit business (e.g. tenant from API). Derive only when unset.
        if self.business_id is None:
            if self.country_id and getattr(self.country, "business_id", None):
                self.business_id = self.country.business_id
            elif self.agency_id:
                self.business_id = _agency_business_pk(self.agency_id)
        if not self.slug:
            self.slug = generate_unique_slug(f"{self.university_name}-{self.country_id}", self)
        super().save(*args, **kwargs)


class UniversityIntake(BaseModel):
    """
    Intake periods available under a university (e.g. June, March, September).
    """

    agency = models.ForeignKey(
        Agency,
        on_delete=models.CASCADE,
        related_name="university_intakes",
        null=True,
        blank=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="business_university_intakes",
        null=True,
        blank=True,
    )
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="intakes")
    intake_name = models.CharField(max_length=50)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.university.university_name} - {self.intake_name}"

    def save(self, *args, **kwargs):
        if self.university_id and self.university.agency_id:
            self.agency_id = self.university.agency_id
        if self.business_id is None and self.university_id and getattr(self.university, "business_id", None):
            self.business_id = self.university.business_id
        if not self.slug and self.university_id:
            self.slug = generate_unique_slug(f"{self.university_id}-{self.intake_name}", self)
        super().save(*args, **kwargs)

class Program(BaseModel):
    agency = models.ForeignKey(
        Agency,
        on_delete=models.CASCADE,
        related_name="tenant_programs",
        null=True,
        blank=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="business_programs",
        null=True,
        blank=True,
    )
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.business_id is None and self.agency_id:
            self.business_id = _agency_business_pk(self.agency_id)
        if not self.slug:
            self.slug = generate_unique_slug(self.name, self)
        super().save(*args, **kwargs)

class UniversityProgram(BaseModel):
    """
    Program options enabled for a university.
    """

    agency = models.ForeignKey(
        Agency,
        on_delete=models.CASCADE,
        related_name="university_program_links",
        null=True,
        blank=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="business_university_program_links",
        null=True,
        blank=True,
    )
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="programs")
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="programs")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.university.university_name} - {self.program}"

    def save(self, *args, **kwargs):
        if self.university_id and self.university.agency_id:
            self.agency_id = self.university.agency_id
        if self.business_id is None and self.university_id and getattr(self.university, "business_id", None):
            self.business_id = self.university.business_id
        if not self.slug and self.university_id:
            self.slug = generate_unique_slug(f"{self.university_id}-{self.program.name}", self)
        super().save(*args, **kwargs)


class UniversityProgramSubject(BaseModel):
    """
    Subject and track rows configured under a university program (e.g. EAP, KLP).
    Matches super-admin "Subjects under program" form sections.
    """

    agency = models.ForeignKey(
        Agency,
        on_delete=models.CASCADE,
        related_name="university_program_subjects",
        null=True,
        blank=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="business_university_program_subjects",
        null=True,
        blank=True,
    )
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    program = models.ForeignKey(UniversityProgram, on_delete=models.CASCADE, related_name="subjects")
    subject_name = models.CharField(max_length=255)
    track_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.program.program.name} — {self.subject_name}"

    def save(self, *args, **kwargs):
        if self.program_id and self.program.agency_id:
            self.agency_id = self.program.agency_id
        if self.business_id is None and self.program_id and getattr(self.program, "business_id", None):
            self.business_id = self.program.business_id
        if not self.slug and self.program_id:
            self.slug = generate_unique_slug(f"{self.program_id}-{self.subject_name}-{self.track_name}", self)
        super().save(*args, **kwargs)


class OfficeCost(BaseModel):
    """
    Office-level operational cost entry.
    """

    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, related_name="office_costs", null=True, blank=True)
    business = models.ForeignKey(
        Business, on_delete=models.SET_NULL, related_name="business_office_costs", null=True, blank=True
    )
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
        if self.business_id is None and self.agency_id:
            self.business_id = _agency_business_pk(self.agency_id)
        if not self.slug:
            self.slug = generate_unique_slug(f"{self.title}-{self.agency_id}", self)
        super().save(*args, **kwargs)


class StudentCost(BaseModel):
    """
    Cost entry tied to a student file (not a customer record).
    """

    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, related_name="student_costs", null=True, blank=True)
    business = models.ForeignKey(
        Business, on_delete=models.SET_NULL, related_name="business_student_costs", null=True, blank=True
    )
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
        if self.business_id is None:
            if self.student_file_id and getattr(self.student_file, "business_id", None):
                self.business_id = self.student_file.business_id
            elif self.agency_id:
                self.business_id = _agency_business_pk(self.agency_id)
        if not self.slug:
            self.slug = generate_unique_slug(f"{self.title}-{self.student_file_id}", self)
        super().save(*args, **kwargs)