from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_address_is_demo_professionalprofile_is_demo_and_more")]

    operations = [
        migrations.CreateModel(
            name="FavoriteProfessional",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorite_professionals", to="accounts.user")),
                ("professional", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorited_by", to="accounts.professionalprofile")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="favoriteprofessional",
            constraint=models.UniqueConstraint(fields=("customer", "professional"), name="unique_customer_favorite_professional"),
        ),
    ]