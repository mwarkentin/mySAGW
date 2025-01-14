# Generated by Django 2.2.18 on 2021-03-15 12:17

from django.db import migrations, models
import localized_fields.fields.text_field
import simple_history.models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="HistoricalSnippet",
            fields=[
                ("history_user_id", models.CharField(max_length=150, null=True)),
                (
                    "id",
                    models.UUIDField(db_index=True, default=uuid.uuid4, editable=False),
                ),
                ("title", models.CharField(max_length=255)),
                (
                    "body",
                    localized_fields.fields.text_field.LocalizedTextField(required=[]),
                ),
                ("archived", models.BooleanField(default=False)),
                (
                    "history_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("history_date", models.DateTimeField()),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical snippet",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": "history_date",
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="Snippet",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                (
                    "body",
                    localized_fields.fields.text_field.LocalizedTextField(required=[]),
                ),
                ("archived", models.BooleanField(default=False)),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
