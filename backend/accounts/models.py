from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Single user table for all three roles. A user is a CUSTOMER or
    PROFESSIONAL from signup; ADMIN accounts are created by staff only
    (there is no public admin signup flow per Section 7 of the proposal).
    """
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        PROFESSIONAL = "PROFESSIONAL", "Professional"
        ADMIN = "ADMIN", "Administrator"

    role = models.CharField(max_length=20, choices=Role.choices)
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(
        help_text="Required at signup — minimum age 18 per Section 11."
    )
    phone_verified = models.BooleanField(default=False)
    is_demo = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"


class Address(models.Model):
    """
    A saved service location — home, office, hotel, senior's home, etc.
    Lat/lng are required: they're what the GPS "Reached" check in
    Section 10 compares against, not the free-text address itself.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=100, blank=True, help_text="e.g. 'Home', 'Office'")
    full_address = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    is_default = models.BooleanField(default=False)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.label or self.full_address} — {self.user}"


class ProfessionalProfile(models.Model):
    """
    One-to-one extension of a PROFESSIONAL user. Working hours, radius,
    and online status are self-set (Section 6) and are locked while a
    booking is active — that lock is enforced at the serializer/view
    layer, not here, since it depends on live booking state.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="professional_profile"
    )
    bio = models.TextField(blank=True)
    years_experience = models.PositiveSmallIntegerField(default=0)
    service_radius_km = models.DecimalField(max_digits=5, decimal_places=1, default=5)
    free_travel_radius_km = models.DecimalField(
        max_digits=5, decimal_places=1, default=5,
        help_text="Distance included free before per-km travel pricing kicks in."
    )
    per_km_travel_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_online = models.BooleanField(
        default=False, help_text="Toggled by the professional to receive Instant requests."
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Only True once verification is APPROVED (see verification app).",
    )
    base_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="professional_base_for",
    )
    service_cities = models.JSONField(
        default=list,
        blank=True,
        help_text="Cities explicitly served by this independent professional.",
    )
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    review_count = models.PositiveIntegerField(default=0)
    stripe_connect_account_id = models.CharField(max_length=255, blank=True)
    stripe_connect_account_type = models.CharField(max_length=30, blank=True)
    stripe_connect_charges_enabled = models.BooleanField(default=False)
    stripe_connect_payouts_enabled = models.BooleanField(default=False)
    is_demo = models.BooleanField(default=False)

    def __str__(self):
        return f"Professional: {self.user}"


class FavoriteProfessional(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorite_professionals")
    professional = models.ForeignKey(ProfessionalProfile, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["customer", "professional"], name="unique_customer_favorite_professional")]
        ordering = ["-created_at"]
