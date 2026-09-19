from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Booking(models.Model):
    """
    Core booking record. INSTANT and SCHEDULED share this table because
    they share ~80% of their fields; the differences (priority_fee vs.
    scheduled_time, reaffirmation logic) are handled in the booking_type
    branch at the service layer, not as separate models.
    """

    class BookingType(models.TextChoices):
        INSTANT = "INSTANT", "Instant"
        SCHEDULED = "SCHEDULED", "Scheduled"

    class Status(models.TextChoices):
        SEARCHING = "SEARCHING", "Searching for a professional"
        PENDING_ACCEPT = "PENDING_ACCEPT", "Awaiting professional response"
        CONFIRMED = "CONFIRMED", "Confirmed"
        AWAITING_REAFFIRMATION = "AWAITING_REAFFIRMATION", "Awaiting 1-hour reaffirmation"
        LEFT = "LEFT", "Professional left"
        REACHED = "REACHED", "Professional reached (GPS-verified)"
        STARTED = "STARTED", "Work started"
        COMPLETED = "COMPLETED", "Work completed — pending customer confirmation"
        CONFIRMED_COMPLETE = "CONFIRMED_COMPLETE", "Customer confirmed completion"
        CANCELLED_CUSTOMER = "CANCELLED_CUSTOMER", "Cancelled by customer"
        CANCELLED_PROFESSIONAL = "CANCELLED_PROFESSIONAL", "Cancelled by professional"
        NO_MATCH = "NO_MATCH", "No professional found in service area"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings_as_customer"
    )
    professional = models.ForeignKey(
        "accounts.ProfessionalProfile", on_delete=models.PROTECT, null=True, blank=True,
        related_name="bookings_as_professional",
        help_text="Null while SEARCHING (instant) or before acceptance.",
    )
    professional_service = models.ForeignKey(
        "catalog.ProfessionalService", on_delete=models.PROTECT, related_name="bookings"
    )
    availability_slot = models.ForeignKey(
        "bookings.AvailabilitySlot",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bookings",
        help_text="Reserved slot for scheduled bookings.",
    )
    address = models.ForeignKey("accounts.Address", on_delete=models.PROTECT, related_name="bookings")

    booking_type = models.CharField(max_length=20, choices=BookingType.choices)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SEARCHING)

    # Price snapshot at booking time — never recompute from the live
    # ProfessionalService price after the fact.
    service_price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = models.PositiveSmallIntegerField(default=60)
    travel_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    priority_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Fixed charge added for Instant bookings only (Section 9).",
    )
    platform_commission = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    scheduled_time = models.DateTimeField(
        null=True, blank=True, help_text="Set for SCHEDULED bookings only."
    )
    reaffirmation_confirmed_by_customer = models.BooleanField(default=False)
    reaffirmation_confirmed_by_professional = models.BooleanField(default=False)

    # GPS check for the "Reached" transition (Section 10) — recorded so
    # it's auditable, not just gate-checked and discarded.
    reached_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    reached_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    before_after_consent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    left_at = models.DateTimeField(null=True, blank=True)
    reached_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    confirmed_complete_at = models.DateTimeField(null=True, blank=True)
    is_demo = models.BooleanField(default=False)

    @property
    def total_amount(self):
        return self.service_price + self.travel_fee + self.priority_fee

    def __str__(self):
        return f"Booking #{self.pk} — {self.customer} / {self.booking_type} / {self.status}"


class BookingService(models.Model):
    """Immutable service snapshots attached to a booking."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="selected_services")
    professional_service = models.ForeignKey("catalog.ProfessionalService", on_delete=models.PROTECT)
    service_price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ("booking", "professional_service")


class BookingDecline(models.Model):
    """
    One row per decline, for both Instant and Scheduled (Section 9).
    A booking can have multiple declines as it's offered to the next
    best match — this is the audit trail the customer's "decline
    reason shown" UI reads from.
    """
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="declines")
    professional = models.ForeignKey("accounts.ProfessionalProfile", on_delete=models.CASCADE)
    reason = models.CharField(max_length=255)
    declined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Decline on booking #{self.booking_id} by {self.professional}"


class BookingStatusEvent(models.Model):
    """
    Append-only log of every status transition. This is what powers
    the stage-by-stage customer notifications (Section 2, step 8) and
    gives you a real audit trail if a customer reports a status that
    "doesn't match reality."
    """
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="status_events")
    status = models.CharField(max_length=30, choices=Booking.Status.choices)
    occurred_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["occurred_at"]

    def __str__(self):
        return f"#{self.booking_id} → {self.status} @ {self.occurred_at:%Y-%m-%d %H:%M}"


class BookingNotification(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="notifications")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="booking_notifications")
    event = models.CharField(max_length=40)
    body = models.CharField(max_length=255)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class AvailabilitySlot(models.Model):
    """
    Real open slots a professional exposes for Scheduled booking
    (Section 9). Simple start/end block model — a booking consumes
    (or splits) a slot rather than the slot being deleted, so the
    calendar view has something to render even for booked time.
    """
    professional = models.ForeignKey(
        "accounts.ProfessionalProfile", on_delete=models.CASCADE, related_name="availability_slots"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.professional} — {self.start_time:%Y-%m-%d %H:%M}"
