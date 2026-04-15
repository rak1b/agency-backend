# Generated manually: University.name -> University.university_name (+ historical table).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agency_inventory", "0007_alter_officecost_agency_alter_studentcost_agency_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="university",
            name="unique_university_name_country",
        ),
        migrations.RenameField(
            model_name="university",
            old_name="name",
            new_name="university_name",
        ),
        migrations.RenameField(
            model_name="historicaluniversity",
            old_name="name",
            new_name="university_name",
        ),
        migrations.AddConstraint(
            model_name="university",
            constraint=models.UniqueConstraint(
                fields=("university_name", "country"),
                name="unique_university_name_country",
            ),
        ),
    ]
