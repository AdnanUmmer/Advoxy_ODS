from datetime import date, timedelta
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Address, ProfessionalProfile, User
from catalog.models import Category, ProfessionalService, Service, SubCategory
from payments.models import PaymentAuthorization

from .models import AvailabilitySlot, Booking, BookingStatusEvent


class DemoBookingToolsTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin@example.com",
            password="strong-password-123",
            role=User.Role.ADMIN,
            date_of_birth=date(1990, 1, 1),
            is_staff=True,
        )
        self.customer = User.objects.create_user(
            username="customer@example.com",
            password="strong-password-123",
            role=User.Role.CUSTOMER,
            date_of_birth=date(1990, 1, 1),
        )
        professional_user = User.objects.create_user(
            username="professional@example.com",
            password="strong-password-123",
            role=User.Role.PROFESSIONAL,
            date_of_birth=date(1990, 1, 1),
        )
        address = Address.objects.create(
            user=self.customer,
            full_address="Demo Home, Calgary, AB",
            latitude="51.0447",
            longitude="-114.0719",
        )
        base_address = Address.objects.create(
            user=professional_user,
            full_address="Demo Studio, Calgary, AB",
            latitude="51.0450",
            longitude="-114.0720",
        )
        professional = ProfessionalProfile.objects.create(
            user=professional_user,
            is_active=True,
            is_online=True,
            base_address=base_address,
        )
        category = Category.objects.create(name="Hair", slug="hair")
        subcategory = SubCategory.objects.create(category=category, name="Men", slug="mens-hair", audience=SubCategory.Audience.MEN)
        service = Service.objects.create(subcategory=subcategory, name="Men's Haircut", slug="mens-haircut")
        professional_service = ProfessionalService.objects.create(
            professional=professional,
            service=service,
            price="45.00",
            duration_minutes=45,
        )
        slot_start = timezone.now() + timedelta(days=1)
        slot = AvailabilitySlot.objects.create(
            professional=professional,
            start_time=slot_start,
            end_time=slot_start + timedelta(hours=3),
        )
        self.booking = Booking.objects.create(
            customer=self.customer,
            professional=professional,
            professional_service=professional_service,
            availability_slot=slot,
            address=address,
            booking_type=Booking.BookingType.SCHEDULED,
            status=Booking.Status.PENDING_ACCEPT,
            service_price="45.00",
            scheduled_time=slot.start_time,
        )

    @override_settings(DEMO_BOOKING_TOOLS_ENABLED=False)
    def test_demo_tools_are_disabled_when_not_configured(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse("demo-scenario"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(DEMO_BOOKING_TOOLS_ENABLED=True, DEBUG=True, STRIPE_SECRET_KEY="sk_test_configured")
    @patch("bookings.demo_views.capture_booking_payment")
    def test_admin_can_drive_demo_lifecycle_and_capture_with_stripe_service(self, capture_payment):
        PaymentAuthorization.objects.create(
            booking=self.booking,
            stripe_payment_intent_id="pi_test_demo",
            amount="45.00",
            status=PaymentAuthorization.Status.AUTHORIZED,
        )
        self.client.force_authenticate(user=self.admin)

        for action, expected in [
            ("accept", Booking.Status.CONFIRMED),
            ("left", Booking.Status.LEFT),
            ("reached", Booking.Status.REACHED),
            ("started", Booking.Status.STARTED),
            ("completed", Booking.Status.COMPLETED),
            ("confirm-complete", Booking.Status.CONFIRMED_COMPLETE),
        ]:
            response = self.client.post(reverse("demo-booking-action", args=[self.booking.id, action]), {}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["status"], expected)

        capture_payment.assert_called_once()
        self.assertTrue(BookingStatusEvent.objects.filter(booking=self.booking, status=Booking.Status.CONFIRMED_COMPLETE).exists())

        review = self.client.post(
            reverse("demo-booking-action", args=[self.booking.id, "review"]),
            {"rating": 5, "comment": "Great demo."},
            format="json",
        )
        self.assertEqual(review.status_code, status.HTTP_200_OK)
        self.assertTrue(review.data["created"])
