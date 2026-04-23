import django.db.models.deletion
import simple_history.models
from django.conf import settings
from django.db import migrations, models


PROGRAM_NAME_BY_LEGACY_CODE = {
    "EAP": "EAP",
    "KLP": "KLP",
    "DIPLOMA": "Diploma",
    "BACHELOR": "Bachelor",
    "MASTER": "Master's",
    "MASTERS": "Master's",
    "PHD": "PhD",
}

PROGRAM_CODE_BY_NAME = {
    "eap": "EAP",
    "klp": "KLP",
    "diploma": "DIPLOMA",
    "bachelor": "BACHELOR",
    "bachelor's": "BACHELOR",
    "bachelors": "BACHELOR",
    "master": "MASTERS",
    "master's": "MASTERS",
    "masters": "MASTERS",
    "phd": "PHD",
}


def _resolve_program_name(raw_value):
    if raw_value is None:
        return None
    normalized_value = str(raw_value).strip()
    if not normalized_value:
        return None
    return PROGRAM_NAME_BY_LEGACY_CODE.get(normalized_value, normalized_value)


def _resolve_program_code(program_name):
    if program_name is None:
        return None
    normalized_name = str(program_name).strip()
    if not normalized_name:
        return None
    return PROGRAM_CODE_BY_NAME.get(normalized_name.lower(), normalized_name.upper())


def migrate_program_values_to_fk(apps, schema_editor):
    Program = apps.get_model("agency_inventory", "Program")
    UniversityProgram = apps.get_model("agency_inventory", "UniversityProgram")
    HistoricalUniversityProgram = apps.get_model("agency_inventory", "HistoricalUniversityProgram")

    program_id_by_old_value = {}

    existing_values = set(UniversityProgram.objects.values_list("program", flat=True))
    existing_values.update(HistoricalUniversityProgram.objects.values_list("program", flat=True))

    for old_value in existing_values:
        program_name = _resolve_program_name(old_value)
        if not program_name:
            continue
        program_obj, _ = Program.objects.get_or_create(
            name=program_name,
            defaults={"description": None},
        )
        program_id_by_old_value[old_value] = program_obj.id

    for university_program in UniversityProgram.objects.all():
        resolved_program_id = program_id_by_old_value.get(university_program.program)
        if resolved_program_id:
            university_program.program_ref_id = resolved_program_id
            university_program.save(update_fields=["program_ref"])

    for historical_university_program in HistoricalUniversityProgram.objects.all():
        resolved_program_id = program_id_by_old_value.get(historical_university_program.program)
        if resolved_program_id:
            historical_university_program.program_ref_id = resolved_program_id
            historical_university_program.save(update_fields=["program_ref"])


def migrate_program_values_back_to_text(apps, schema_editor):
    UniversityProgram = apps.get_model("agency_inventory", "UniversityProgram")
    HistoricalUniversityProgram = apps.get_model("agency_inventory", "HistoricalUniversityProgram")

    for university_program in UniversityProgram.objects.select_related("program_ref").all():
        resolved_program_code = _resolve_program_code(getattr(university_program.program_ref, "name", None))
        if resolved_program_code:
            university_program.program = resolved_program_code
            university_program.save(update_fields=["program"])

    for historical_university_program in HistoricalUniversityProgram.objects.select_related("program_ref").all():
        resolved_program_code = _resolve_program_code(getattr(historical_university_program.program_ref, "name", None))
        if resolved_program_code:
            historical_university_program.program = resolved_program_code
            historical_university_program.save(update_fields=["program"])


class Migration(migrations.Migration):

    dependencies = [
        ("agency_inventory", "0015_agency_commission_rate_agency_trade_license_no_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HistoricalProgram",
            fields=[
                ("id", models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name="ID")),
                ("created_at", models.DateTimeField(blank=True, editable=False)),
                ("updated_at", models.DateTimeField(blank=True, editable=False)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("slug", models.SlugField(blank=True, editable=False, max_length=255, null=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical program",
                "verbose_name_plural": "historical programs",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="Program",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("slug", models.SlugField(blank=True, editable=False, max_length=255, null=True, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.RemoveConstraint(
            model_name="universityprogram",
            name="unique_program_per_university",
        ),
        migrations.AddField(
            model_name="historicaluniversityprogram",
            name="program_ref",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="agency_inventory.program",
            ),
        ),
        migrations.AddField(
            model_name="universityprogram",
            name="program_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="university_programs",
                to="agency_inventory.program",
            ),
        ),
        migrations.RunPython(migrate_program_values_to_fk, migrate_program_values_back_to_text),
        migrations.RemoveField(
            model_name="historicaluniversityprogram",
            name="program",
        ),
        migrations.RemoveField(
            model_name="universityprogram",
            name="program",
        ),
        migrations.RenameField(
            model_name="historicaluniversityprogram",
            old_name="program_ref",
            new_name="program",
        ),
        migrations.RenameField(
            model_name="universityprogram",
            old_name="program_ref",
            new_name="program",
        ),
        migrations.AlterField(
            model_name="historicaluniversityprogram",
            name="program",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="agency_inventory.program",
            ),
        ),
        migrations.AlterField(
            model_name="universityprogram",
            name="program",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="programs",
                to="agency_inventory.program",
            ),
        ),
        migrations.AddConstraint(
            model_name="universityprogram",
            constraint=models.UniqueConstraint(fields=("university", "program"), name="unique_program_per_university"),
        ),
    ]
