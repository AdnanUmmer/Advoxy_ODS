import hashlib
import hmac
import json
from datetime import date
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import ProfessionalProfile, User

from .models import ProfessionalVerification


class VerificationApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pro@example.com",
            email="pro@example.com",
            first_name="Priya",
            last_name="Pro",
            password="strong-password-123",
            role=User.Role.PROFESSIONAL,
            date_of_birth=date(1990, 1, 1),
        )
        self.profile = ProfessionalProfile.objects.create(user=self.user)

    @override_settings(PERSONA_API_KEY="", PERSONA_TEMPLATE_ID="", IDENTITY_VERIFICATION_PROVIDER="PERSONA")
    def test_submit_requires_configured_provider(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("verification-submit"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @override_settings(
        PERSONA_API_KEY="persona_sandbox_key",
        PERSONA_TEMPLATE_ID="itmpl_123",
        PERSONA_API_BASE_URL="https://persona.test/api/v1",
    )
    @patch("verification.services.requests.post")
    def test_submit_creates_persona_reference_without_storing_documents(self, post):
        post.return_value.status_code = 201
        post.return_value.json.return_value = {"data": {"id": "inq_123"}}
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("verification-submit"), {"provider": "PERSONA"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["provider_reference_id"], "inq_123")
        verification = ProfessionalVerification.objects.get(professional=self.user.professional_profile)
        self.assertEqual(verification.status, ProfessionalVerification.Status.PENDING)

    @override_settings(PERSONA_WEBHOOK_SECRET="secret")
    def test_persona_webhook_approves_professional_with_valid_signature(self):
        verification = ProfessionalVerification.objects.create(
            professional=self.profile,
            provider=ProfessionalVerification.Provider.PERSONA,
            provider_reference_id="inq_approved",
            status=ProfessionalVerification.Status.PENDING,
            fee_paid=True,
        )
        payload = {
            "data": {
                "attributes": {
                    "name": "inquiry.approved",
                    "payload": {"data": {"id": "inq_approved"}},
                }
            }
        }
        body = json.dumps(payload).encode("utf-8")
        timestamp = "1700000000"
        signature = hmac.new(b"secret", timestamp.encode("utf-8") + b"." + body, hashlib.sha256).hexdigest()
        response = self.client.post(
            reverse("persona-webhook"),
            data=body,
            content_type="application/json",
            HTTP_PERSONA_SIGNATURE=f"t={timestamp},v1={signature}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        verification.refresh_from_db()
        self.user.professional_profile.refresh_from_db()
        self.assertEqual(verification.status, ProfessionalVerification.Status.APPROVED)
        self.assertTrue(self.user.professional_profile.is_active)
