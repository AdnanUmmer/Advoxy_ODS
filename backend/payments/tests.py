from decimal import Decimal
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Address, ProfessionalProfile, User
from bookings.models import Booking
from catalog.models import Category, ProfessionalService, Service, SubCategory

from .models import PaymentAuthorization, Payout, StripeEvent


class PaymentApiTests(APITestCase):
	def setUp(self):
		self.customer = User.objects.create_user(
			username="payer@example.com", password="strong-password-123",
			role=User.Role.CUSTOMER, date_of_birth=date(1990, 1, 1),
		)
		professional_user = User.objects.create_user(
			username="payee@example.com", password="strong-password-123",
			role=User.Role.PROFESSIONAL, date_of_birth=date(1985, 1, 1),
		)
		professional = ProfessionalProfile.objects.create(user=professional_user, is_active=True)
		address = Address.objects.create(
			user=self.customer, full_address="123 4 Street SW", latitude="51.0447", longitude="-114.0719"
		)
		category = Category.objects.create(name="Hair", slug="hair")
		subcategory = SubCategory.objects.create(category=category, name="Colour", slug="colour")
		service = Service.objects.create(subcategory=subcategory, name="Balayage")
		professional_service = ProfessionalService.objects.create(
			professional=professional, service=service, price="100.00", duration_minutes=60
		)
		self.booking = Booking.objects.create(
			customer=self.customer, professional=professional,
			professional_service=professional_service, address=address,
			booking_type=Booking.BookingType.SCHEDULED,
			status=Booking.Status.CONFIRMED, service_price="100.00",
		)
		self.client.force_authenticate(user=self.customer)

	@override_settings(STRIPE_SECRET_KEY="")
	def test_payment_does_not_fake_success_without_stripe_configuration(self):
		response = self.client.post(reverse("payment-intent"), {"booking": self.booking.id}, format="json")
		self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
		self.assertFalse(PaymentAuthorization.objects.exists())

	@override_settings(STRIPE_SECRET_KEY="sk_test_configured")
	@patch("payments.views.stripe.PaymentIntent.create")
	def test_payment_uses_server_total_and_stores_authorization(self, create_intent):
		create_intent.return_value = SimpleNamespace(
			id="pi_test_123", client_secret="secret_123", status="requires_capture"
		)
		response = self.client.post(
			reverse("payment-intent"), {"booking": self.booking.id, "amount": "1.00"}, format="json"
		)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(PaymentAuthorization.objects.get().amount, Decimal("100.00"))
		self.assertEqual(create_intent.call_args.kwargs["amount"], 10000)
		self.assertEqual(create_intent.call_args.kwargs["capture_method"], "manual")
		self.assertEqual(create_intent.call_args.kwargs["payment_method_types"], ["card"])

	@override_settings(STRIPE_SECRET_KEY="sk_test_configured")
	@patch("payments.views.stripe.PaymentIntent.retrieve")
	def test_payment_confirmation_marks_authorization_as_authorized(self, retrieve_intent):
		PaymentAuthorization.objects.create(
			booking=self.booking,
			stripe_payment_intent_id="pi_confirmed",
			amount="100.00",
			status=PaymentAuthorization.Status.PENDING,
		)
		retrieve_intent.return_value = SimpleNamespace(status="requires_capture")
		response = self.client.post(
			reverse("payment-confirm"),
			{"payment_intent_id": "pi_confirmed"},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["status"], PaymentAuthorization.Status.AUTHORIZED)

	@override_settings(STRIPE_WEBHOOK_SECRET="whsec_configured")
	@patch("payments.views.stripe.Webhook.construct_event")
	def test_webhook_rejects_invalid_signature(self, construct_event):
		import stripe

		construct_event.side_effect = stripe.error.SignatureVerificationError("bad", "sig")
		response = self.client.post(reverse("stripe-webhook"), data=b"{}", content_type="application/json")
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	@override_settings(STRIPE_WEBHOOK_SECRET="whsec_configured")
	@patch("payments.views.stripe.Webhook.construct_event")
	def test_duplicate_capture_webhook_is_idempotent(self, construct_event):
		PaymentAuthorization.objects.create(
			booking=self.booking,
			stripe_payment_intent_id="pi_capture",
			amount="100.00",
			status=PaymentAuthorization.Status.AUTHORIZED,
		)
		event = {
			"id": "evt_capture_1",
			"type": "payment_intent.succeeded",
			"data": {"object": {"id": "pi_capture"}},
		}
		construct_event.return_value = event
		first = self.client.post(reverse("stripe-webhook"), data=b"{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="valid")
		second = self.client.post(reverse("stripe-webhook"), data=b"{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="valid")
		self.assertEqual(first.status_code, status.HTTP_200_OK)
		self.assertEqual(second.status_code, status.HTTP_200_OK)
		self.assertEqual(StripeEvent.objects.count(), 1)
		self.assertEqual(PaymentAuthorization.objects.get().status, PaymentAuthorization.Status.CAPTURED)
		self.assertEqual(Payout.objects.count(), 1)
