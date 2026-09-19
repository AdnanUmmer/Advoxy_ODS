from django.db import models


class PaymentAuthorization(models.Model):
    """
    Section 12's escrow flow: authorize at booking, capture only on
    confirmed completion. One row per booking — this table's status
    IS the escrow state machine.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Payment method confirmation pending"
        AUTHORIZED = "AUTHORIZED", "Authorized (held)"
        CAPTURED = "CAPTURED", "Captured"
        CANCELLED = "CANCELLED", "Authorization cancelled (no charge)"
        REFUNDED = "REFUNDED", "Refunded after capture"
        FAILED = "FAILED", "Payment failed"

    class Provider(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        DEMO = "demo", "Demo"

    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.PROTECT, related_name="payment_authorization"
    )
    stripe_payment_intent_id = models.CharField(max_length=255)
    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.STRIPE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AUTHORIZED)

    authorized_at = models.DateTimeField(auto_now_add=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.CharField(
        max_length=255, blank=True, help_text="Set when admin adjusts/refunds from the dashboard."
    )
    is_demo = models.BooleanField(default=False)

    def __str__(self):
        return f"Payment for booking #{self.booking_id} — {self.status}"


class Payout(models.Model):
    """
    Section 12, step 3: released after commission deduction and the
    mandatory dispute window. released_at is null until that window
    clears — that's the field a background job checks.
    """
    booking = models.OneToOneField("bookings.Booking", on_delete=models.PROTECT, related_name="payout")
    professional = models.ForeignKey(
        "accounts.ProfessionalProfile", on_delete=models.PROTECT, related_name="payouts"
    )
    gross_amount = models.DecimalField(max_digits=8, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=8, decimal_places=2)
    net_amount = models.DecimalField(max_digits=8, decimal_places=2)
    stripe_transfer_id = models.CharField(max_length=255, blank=True)
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending provider transfer"
        PROCESSING = "PROCESSING", "Transfer processing"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Transfer failed"
        REVERSED = "REVERSED", "Transfer reversed"

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider_error = models.CharField(max_length=255, blank=True)

    dispute_window_ends_at = models.DateTimeField()
    released_at = models.DateTimeField(null=True, blank=True)
    is_demo = models.BooleanField(default=False)

    def __str__(self):
        return f"Payout — {self.professional} — ${self.net_amount}"


class StripeEvent(models.Model):
    """Processed Stripe event IDs make webhook retries harmless."""

    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    received_at = models.DateTimeField(auto_now_add=True)
