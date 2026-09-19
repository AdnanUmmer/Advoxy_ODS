from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="professionalprofile",
            name="service_cities",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Cities explicitly served by this independent professional.",
            ),
        ),
    ]