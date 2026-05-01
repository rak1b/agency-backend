# Data backfill: one ``Business`` per existing ``Agency``, then propagate ``business_id``.

from django.db import migrations


def forwards(apps, schema_editor):
    Agency = apps.get_model("agency_inventory", "Agency")
    Business = apps.get_model("agency_inventory", "Business")

    Customer = apps.get_model("agency_inventory", "Customer")
    StudentFile = apps.get_model("agency_inventory", "StudentFile")
    StudentFileAttachment = apps.get_model("agency_inventory", "StudentFileAttachment")
    AppliedUniversity = apps.get_model("agency_inventory", "AppliedUniversity")
    Country = apps.get_model("agency_inventory", "Country")
    University = apps.get_model("agency_inventory", "University")
    UniversityIntake = apps.get_model("agency_inventory", "UniversityIntake")
    Program = apps.get_model("agency_inventory", "Program")
    UniversityProgram = apps.get_model("agency_inventory", "UniversityProgram")
    UniversityProgramSubject = apps.get_model("agency_inventory", "UniversityProgramSubject")
    OfficeCost = apps.get_model("agency_inventory", "OfficeCost")
    StudentCost = apps.get_model("agency_inventory", "StudentCost")

    for agency in Agency.objects.all().iterator():
        if agency.business_id:
            continue
        biz = Business.objects.create(
            name=agency.name,
            owner_name=agency.owner_name or "",
            status=agency.status or "ACTIVE",
            business_email=getattr(agency, "business_email", None),
            phone=agency.phone or "",
            address=agency.address or "",
            logo_image_url=getattr(agency, "logo_image_url", None),
        )
        Agency.objects.filter(pk=agency.pk).update(business_id=biz.pk)

    agency_to_business = {row[0]: row[1] for row in Agency.objects.values_list("id", "business_id")}

    def propagate_from_agency_fk(model_cls, agency_field="agency_id"):
        missing = model_cls.objects.filter(business_id__isnull=True).exclude(**{agency_field: None})
        for row in missing.iterator():
            bid = agency_to_business.get(getattr(row, agency_field))
            if bid:
                model_cls.objects.filter(pk=row.pk).update(business_id=bid)

    for model in (
        Customer,
        StudentFile,
        StudentFileAttachment,
        AppliedUniversity,
        Country,
        University,
        UniversityIntake,
        Program,
        UniversityProgram,
        UniversityProgramSubject,
    ):
        propagate_from_agency_fk(model, "agency_id")

    propagate_from_agency_fk(OfficeCost, "agency_id")

    sf_business = {
        row[0]: row[1]
        for row in StudentFile.objects.exclude(business_id__isnull=True).values_list("id", "business_id")
    }
    for row in StudentCost.objects.filter(business_id__isnull=True).exclude(student_file_id__isnull=True).iterator():
        bid = sf_business.get(row.student_file_id)
        if bid:
            StudentCost.objects.filter(pk=row.pk).update(business_id=bid)
    propagate_from_agency_fk(StudentCost, "agency_id")


def noop_reverse(_apps, _schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("agency_inventory", "0019_business_agency_business_applieduniversity_business_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, noop_reverse),
    ]
