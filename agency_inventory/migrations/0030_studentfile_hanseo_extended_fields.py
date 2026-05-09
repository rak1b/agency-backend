# Generated manually for Hanseo PDF / extended student profile fields.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agency_inventory", "0029_historicalstudentfile_passport_photo_url_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalstudentfile",
            name="gender",
            field=models.CharField(
                choices=[("MALE", "Male"), ("FEMALE", "Female"), ("OTHER", "Other")],
                default="OTHER",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="historicalstudentfile",
            name="nationality",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="historicalstudentfile",
            name="place_of_birth",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="historicalstudentfile",
            name="present_address",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="historicalstudentfile",
            name="permanent_address",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="historicalstudentfile",
            name="education_background",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historicalstudentfile",
            name="family_particulars",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historicalstudentfile",
            name="translator_profile",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historicalstudentfile",
            name="translated_documents_note",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="historicalstudentfile",
            name="application_statement",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="historicalstudentfile",
            name="highest_education_postal_code",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AddField(
            model_name="historicalstudentfile",
            name="highest_education_address",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="historicalstudentfile",
            name="highest_education_fax",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="historicalstudentfile",
            name="highest_education_website",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="gender",
            field=models.CharField(
                choices=[("MALE", "Male"), ("FEMALE", "Female"), ("OTHER", "Other")],
                default="OTHER",
                help_text="Stored like Customer; shown on Hanseo and similar admission forms.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="nationality",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="place_of_birth",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="present_address",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="permanent_address",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="education_background",
            field=models.JSONField(
                blank=True,
                help_text="Rows for Hanseo academic table: degree, institution, study_period, result, graduation_date, institution_phone, admission_date (optional).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="family_particulars",
            field=models.JSONField(
                blank=True,
                help_text="Rows: relation, name, date_of_birth, occupation, monthly_income, workplace, workplace_phone.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="translator_profile",
            field=models.JSONField(
                blank=True,
                help_text="Optional Hanseo page-3 translator: nationality, name, date_of_birth, gender, address, home_phone, mobile.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="translated_documents_note",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Short list for the Hanseo translation form (e.g. APPLICANT NID, PARENTS NID).",
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="application_statement",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Statement of purpose line on page 1 of the Hanseo pack; a sensible default is applied in the PDF if empty.",
            ),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="highest_education_postal_code",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="highest_education_address",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="highest_education_fax",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="studentfile",
            name="highest_education_website",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
