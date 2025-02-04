# Generated by Django 4.1 on 2023-11-15 15:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("voting", "0004_alter_voting_postproc_alter_voting_tally"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="question_type",
            field=models.CharField(
                choices=[("DEFAULT", "Default"), ("YESNO", "Yes/No")],
                default="DEFAULT",
                max_length=20,
            ),
        ),
    ]
