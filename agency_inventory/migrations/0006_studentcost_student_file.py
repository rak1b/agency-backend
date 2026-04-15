# Generated manually for StudentCost.customer -> StudentCost.student_file

import django.db.models.deletion
from django.db import migrations, models


def forwards_assign_student_file(apps, schema_editor):
    """
    Map legacy customer -> student_file by matching passport_number.
    Rows that cannot be matched are hard-deleted so student_file can be NOT NULL.
    """
    StudentCost = apps.get_model("agency_inventory", "StudentCost")
    StudentFile = apps.get_model("agency_inventory", "StudentFile")
    db_alias = schema_editor.connection.alias

    for cost in StudentCost.objects.using(db_alias).all().iterator():
        customer_id = getattr(cost, "customer_id", None)
        if not customer_id:
            continue
        customer = cost.customer
        passport = getattr(customer, "passport_number", None)
        if not passport:
            continue
        student_file = StudentFile.objects.using(db_alias).filter(passport_number=passport).first()
        if student_file:
            cost.student_file_id = student_file.id
            cost.save(update_fields=["student_file_id"])

    StudentCost.objects.using(db_alias).filter(student_file_id__isnull=True)._raw_delete(using=db_alias)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("agency_inventory", "0005_universityprogramsubject"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalstudentcost",
            name="student_file",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="agency_inventory.studentfile",
            ),
        ),
        migrations.AddField(
            model_name="studentcost",
            name="student_file",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="costs",
                to="agency_inventory.studentfile",
            ),
        ),
        migrations.RunPython(forwards_assign_student_file, noop_reverse),
        migrations.RemoveField(
            model_name="studentcost",
            name="customer",
        ),
        migrations.RemoveField(
            model_name="historicalstudentcost",
            name="customer",
        ),
        migrations.AlterField(
            model_name="studentcost",
            name="student_file",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="costs",
                to="agency_inventory.studentfile",
            ),
        ),
    ]
