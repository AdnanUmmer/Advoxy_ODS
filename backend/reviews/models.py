from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    """
    Section 6: reviews are mutual, not one-directional — the customer
    reviews the professional AND the professional reviews the customer.
    Modeled as two rows per booking (direction implicit in reviewer/
    reviewee) rather than a single row with two rating columns, so the
    "visible on profile" query is a plain filter on reviewee.
    """
    booking = models.ForeignKey("bookings.Booking", on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_given"
    )
    reviewee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_received"
    )
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Flagged automatically for admin review on 1–2 star ratings
    # (Section 7) — computed on save, not recalculated by the admin UI.
    flagged_for_admin = models.BooleanField(default=False)
    is_demo = models.BooleanField(default=False)

    class Meta:
        unique_together = ("booking", "reviewer")

    def save(self, *args, **kwargs):
        self.flagged_for_admin = self.rating <= 2
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reviewer} → {self.reviewee}: {self.rating}★"
