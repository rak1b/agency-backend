# Generated manually — assigns a fallback agency to legacy rows with NULL agency_id.

from django.db import migrations


def backfill_agency_columns(apps, schema_editor):
    Agency = apps.get_model("agency_inventory", "Agency")
    fallback = Agency.objects.order_by("pk").first()
    if not fallback:
        return

    Country = apps.get_model("agency_inventory", "Country")
    Country.objects.filter(agency__isnull=True).update(agency_id=fallback.pk)

    University = apps.get_model("agency_inventory", "University")
    for uni in University.objects.filter(agency__isnull=True).select_related("country"):
        cid = getattr(uni, "country_id", None)
        if cid:
            c = Country.objects.filter(pk=cid).first()
            if c and c.agency_id:
                University.objects.filter(pk=uni.pk).update(agency_id=c.agency_id)
                continue
        University.objects.filter(pk=uni.pk).update(agency_id=fallback.pk)

    Program = apps.get_model("agency_inventory", "Program")
    Program.objects.filter(agency__isnull=True).update(agency_id=fallback.pk)

    UniversityIntake = apps.get_model("agency_inventory", "UniversityIntake")
    for row in UniversityIntake.objects.filter(agency__isnull=True).select_related("university"):
        aid = row.university.agency_id if row.university_id else None
        if aid:
            UniversityIntake.objects.filter(pk=row.pk).update(agency_id=aid)
        else:
            UniversityIntake.objects.filter(pk=row.pk).update(agency_id=fallback.pk)

    UniversityProgram = apps.get_model("agency_inventory", "UniversityProgram")
    for row in UniversityProgram.objects.filter(agency__isnull=True).select_related("university"):
        aid = row.university.agency_id if row.university_id else None
        if aid:
            UniversityProgram.objects.filter(pk=row.pk).update(agency_id=aid)
        else:
            UniversityProgram.objects.filter(pk=row.pk).update(agency_id=fallback.pk)

    UniversityProgramSubject = apps.get_model("agency_inventory", "UniversityProgramSubject")
    for row in UniversityProgramSubject.objects.filter(agency__isnull=True).select_related("program__university"):
        aid = None
        if row.program_id and row.program.university_id:
            aid = row.program.university.agency_id
        if aid:
            UniversityProgramSubject.objects.filter(pk=row.pk).update(agency_id=aid)
        else:
            UniversityProgramSubject.objects.filter(pk=row.pk).update(agency_id=fallback.pk)

    AppliedUniversity = apps.get_model("agency_inventory", "AppliedUniversity")
    for row in AppliedUniversity.objects.filter(agency__isnull=True).select_related("university", "country"):
        aid = row.university.agency_id if row.university_id else None
        if not aid and row.country_id:
            c = Country.objects.filter(pk=row.country_id).first()
            aid = c.agency_id if c else None
        if aid:
            AppliedUniversity.objects.filter(pk=row.pk).update(agency_id=aid)
        else:
            AppliedUniversity.objects.filter(pk=row.pk).update(agency_id=fallback.pk)

    StudentFile = apps.get_model("agency_inventory", "StudentFile")
    StudentFile.objects.filter(agency__isnull=True).update(agency_id=fallback.pk)

    StudentFileAttachment = apps.get_model("agency_inventory", "StudentFileAttachment")
    StudentFileAttachment.objects.filter(agency__isnull=True).update(agency_id=fallback.pk)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("agency_inventory", "0017_tenant_agency_scope"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_columns, noop_reverse),
    ]
