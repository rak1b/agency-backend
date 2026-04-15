# Align UniversityProgram.program with frontend PROGRAM_LEVELS (MASTERS) and refresh choices.

from django.db import migrations, models


def forwards_master_to_masters(apps, schema_editor):
    UniversityProgram = apps.get_model("agency_inventory", "UniversityProgram")
    HistoricalUniversityProgram = apps.get_model("agency_inventory", "HistoricalUniversityProgram")
    UniversityProgram.objects.filter(program="MASTER").update(program="MASTERS")
    HistoricalUniversityProgram.objects.filter(program="MASTER").update(program="MASTERS")


def reverse_masters_to_master(apps, schema_editor):
    UniversityProgram = apps.get_model("agency_inventory", "UniversityProgram")
    HistoricalUniversityProgram = apps.get_model("agency_inventory", "HistoricalUniversityProgram")
    UniversityProgram.objects.filter(program="MASTERS").update(program="MASTER")
    HistoricalUniversityProgram.objects.filter(program="MASTERS").update(program="MASTER")


class Migration(migrations.Migration):

    dependencies = [
        ("agency_inventory", "0008_rename_university_name_to_university_name"),
    ]

    operations = [
        migrations.RunPython(forwards_master_to_masters, reverse_masters_to_master),
        migrations.AlterField(
            model_name="universityprogram",
            name="program",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("EAP", "EAP"),
                    ("KLP", "KLP"),
                    ("DIPLOMA", "Diploma"),
                    ("BACHELOR", "Bachelor"),
                    ("MASTERS", "Master's"),
                    ("PHD", "PhD"),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="historicaluniversityprogram",
            name="program",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("EAP", "EAP"),
                    ("KLP", "KLP"),
                    ("DIPLOMA", "Diploma"),
                    ("BACHELOR", "Bachelor"),
                    ("MASTERS", "Master's"),
                    ("PHD", "PhD"),
                ],
            ),
        ),
    ]
