from django.db import models


class ProfessionalVerification(models.Model):
    """
    Section 11: the platform does NOT store raw government ID copies —
    only the provider's reference ID and outcome. Do not add an
    ID-image field here; that upload goes straight to the provider
    (Certn/Persona) from the client, never through our storage.
    """

    class Provider(models.TextChoices):
        CERTN = "CERTN", "Certn"
        PERSONA = "PERSONA", "Persona"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired — re-verification required"

    professional = models.OneToOneField(
        "accounts.ProfessionalProfile", on_delete=models.CASCADE, related_name="verification"
    )
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_reference_id = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    fee_paid = models.BooleanField(
        default=False,
        help_text="Submission is only sent to the provider once this is True (Section 11, step 2).",
    )
    identity_check_passed = models.BooleanField(null=True, blank=True)
    criminal_record_check_passed = models.BooleanField(null=True, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="verification_decisions",
        help_text="Admin who approved/rejected in the dashboard.",
    )
    expires_at = models.DateTimeField(
        null=True, blank=True, help_text="Annual re-verification per Section 11, step 6."
    )
    is_demo = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.professional} — {self.status}"
