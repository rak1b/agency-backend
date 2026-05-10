from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agency_inventory", "0036_alter_historicalstudentfamilyparticular_monthly_income_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalstudentfile",
            name="signature_url",
            field=models.URLField(blank=True, max_length=1000, null=True),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="signature_url",
            field=models.URLField(
                blank=True,
                help_text="Student signature image URL",
                max_length=1000,
                null=True,
            ),
        ),
    ]
