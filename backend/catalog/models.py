from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Category(models.Model):
    """Top-level: Hair, Nails (Section 5/6)."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    class Audience(models.TextChoices):
        MEN = "MEN", "Men"
        WOMEN = "WOMEN", "Women"
        KIDS = "KIDS", "Kids"
        UNISEX = "UNISEX", "Unisex"

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.UNISEX)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_demo = models.BooleanField(default=False)

    class Meta:
        unique_together = ("category", "slug")
        verbose_name_plural = "Subcategories"

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class Service(models.Model):
    """
    A bookable service definition (e.g. 'Balayage', 'Gel manicure').
    This is the catalog entry — actual price/duration is set per
    professional in ProfessionalService below, per Section 6.
    """
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveSmallIntegerField(
        default=60,
        validators=[MinValueValidator(1), MaxValueValidator(480)],
    )
    is_active = models.BooleanField(default=True)
    slug = models.SlugField(blank=True)
    parent_service = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="variants"
    )
    default_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_demo = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class ProfessionalService(models.Model):
    """
    A professional's own price and duration for a catalog service.
    This is what actually gets booked — Booking.service points here,
    not to Service directly, so historical bookings keep the price
    that was in effect at booking time via the snapshot on Booking.
    """
    professional = models.ForeignKey(
        "accounts.ProfessionalProfile", on_delete=models.CASCADE, related_name="services_offered"
    )
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="offered_by")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        unique_together = ("professional", "service")

    def __str__(self):
        return f"{self.professional} — {self.service} (${self.price})"


class MarketplaceSettings(models.Model):
    """Admin-controlled defaults used by search, booking, and payments."""

    instant_initial_radius_km = models.DecimalField(max_digits=6, decimal_places=2, default=10, validators=[MinValueValidator(0)])
    instant_max_radius_km = models.DecimalField(max_digits=6, decimal_places=2, default=25, validators=[MinValueValidator(0)])
    scheduled_search_radius_km = models.DecimalField(max_digits=6, decimal_places=2, default=25, validators=[MinValueValidator(0)])
    radius_expansion_step_km = models.DecimalField(max_digits=6, decimal_places=2, default=5, validators=[MinValueValidator(0)])
    professional_service_radius_km = models.DecimalField(max_digits=6, decimal_places=2, default=25, validators=[MinValueValidator(0)])
    maximum_travel_distance_km = models.DecimalField(max_digits=6, decimal_places=2, default=25, validators=[MinValueValidator(0)])

    included_travel_distance_km = models.DecimalField(max_digits=6, decimal_places=2, default=5, validators=[MinValueValidator(0)])
    travel_fee_per_km = models.DecimalField(max_digits=8, decimal_places=2, default=2, validators=[MinValueValidator(0)])
    maximum_travel_fee = models.DecimalField(max_digits=8, decimal_places=2, default=20, validators=[MinValueValidator(0)])
    minimum_booking_price = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=20, validators=[MinValueValidator(0), MaxValueValidator(100)])
    fixed_platform_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    minimum_platform_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    maximum_platform_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    customer_cancellation_window_minutes = models.PositiveIntegerField(default=60)
    professional_acceptance_window_minutes = models.PositiveIntegerField(default=10)
    scheduled_minimum_notice_minutes = models.PositiveIntegerField(default=0)
    maximum_advance_booking_days = models.PositiveIntegerField(default=365)
    instant_booking_timeout_minutes = models.PositiveIntegerField(default=10)
    rematching_timeout_minutes = models.PositiveIntegerField(default=10)
    reminder_minutes_before_booking = models.PositiveIntegerField(default=60)
    rematching_enabled = models.BooleanField(default=True)
    instant_booking_enabled = models.BooleanField(default=True)
    scheduled_booking_enabled = models.BooleanField(default=True)
    multiple_service_booking_enabled = models.BooleanField(default=True)
    travel_fees_enabled = models.BooleanField(default=True)

    availability_weight = models.PositiveIntegerField(default=100)
    distance_weight = models.PositiveIntegerField(default=50)
    rating_weight = models.PositiveIntegerField(default=20)
    review_count_weight = models.PositiveIntegerField(default=10)
    experience_weight = models.PositiveIntegerField(default=5)
    reliability_weight = models.PositiveIntegerField(default=5)

    tax_enabled = models.BooleanField(default=False)
    tax_name = models.CharField(max_length=100, blank=True)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Marketplace settings"
        verbose_name_plural = "Marketplace settings"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.instant_max_radius_km < self.instant_initial_radius_km:
            raise ValidationError({"instant_max_radius_km": "Maximum instant radius cannot be lower than the initial radius."})
        if self.maximum_travel_distance_km < self.included_travel_distance_km:
            raise ValidationError({"maximum_travel_distance_km": "Maximum travel distance cannot be lower than included distance."})

    @classmethod
    def current(cls):
        settings_object, _ = cls.objects.get_or_create(pk=1)
        return settings_object


class MarketplaceSettingsAudit(models.Model):
    settings = models.ForeignKey(MarketplaceSettings, on_delete=models.CASCADE, related_name="audit_entries")
    admin = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    changes = models.JSONField(default=dict)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
