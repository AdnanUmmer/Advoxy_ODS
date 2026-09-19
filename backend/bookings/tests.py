from datetime import date, datetime, timezone as dt_timezone

from django.urls import reverse
from django.utils import timezone
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Address, ProfessionalProfile, User
from catalog.models import Category, MarketplaceSettings, ProfessionalService, Service, SubCategory

from .models import AvailabilitySlot, Booking


class BookingApiTests(APITestCase):
	def setUp(self):
		self.customer = User.objects.create_user(
			username="customer@example.com",
			email="customer@example.com",
			password="strong-password-123",
			role=User.Role.CUSTOMER,
			date_of_birth=date(1990, 1, 1),
		)
		self.other_customer = User.objects.create_user(
			username="other@example.com",
			email="other@example.com",
			password="strong-password-123",
			role=User.Role.CUSTOMER,
			date_of_birth=date(1990, 1, 1),
		)
		self.address = Address.objects.create(
			user=self.customer,
			label="Home",
			full_address="123 4 Street SW, Calgary",
			latitude="51.0447",
			longitude="-114.0719",
			is_default=True,
		)
		other_address = Address.objects.create(
			user=self.other_customer,
			label="Home",
			full_address="999 Other Street SW, Calgary",
			latitude="51.0447",
			longitude="-114.0719",
		)
		professional_user = User.objects.create_user(
			username="pro@example.com",
			email="pro@example.com",
			password="strong-password-123",
			role=User.Role.PROFESSIONAL,
			date_of_birth=date(1985, 1, 1),
			first_name="Maya",
			last_name="Pro",
		)
		professional_address = Address.objects.create(
			user=professional_user,
			label="Studio",
			full_address="123 4 Street SW, Calgary",
			latitude="51.0447",
			longitude="-114.0719",
		)
		self.professional = ProfessionalProfile.objects.create(
			user=professional_user,
			is_active=True,
			average_rating="4.90",
			base_address=professional_address,
		)
		category = Category.objects.create(name="Hair", slug="hair")
		subcategory = SubCategory.objects.create(category=category, name="Colour", slug="colour")
		service = Service.objects.create(subcategory=subcategory, name="Balayage", is_active=True)
		self.professional_service = ProfessionalService.objects.create(
			professional=self.professional,
			service=service,
			price="125.00",
			duration_minutes=90,
		)
		self.slot = AvailabilitySlot.objects.create(
			professional=self.professional,
			start_time=datetime(2030, 1, 1, 17, 0, tzinfo=dt_timezone.utc),
			end_time=datetime(2030, 1, 1, 20, 0, tzinfo=dt_timezone.utc),
		)
		marketplace_settings = MarketplaceSettings.current()
		marketplace_settings.maximum_advance_booking_days = 2000
		marketplace_settings.save(update_fields=["maximum_advance_booking_days"])
		self.other_address = other_address
		self.client.force_authenticate(user=self.customer)

	def test_scheduled_booking_snapshots_price_and_assigns_professional(self):
		response = self.client.post(
			reverse("booking-list"),
			{
				"professional_service": self.professional_service.id,
				"address": self.address.id,
				"booking_type": "SCHEDULED",
				"scheduled_time": "2030-01-01T18:00:00Z",
			},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data["status"], "PENDING_ACCEPT")
		self.assertEqual(response.data["service_price"], "125.00")
		self.assertEqual(response.data["professional"], self.professional.id)
		self.assertEqual(response.data["availability_slot"], self.slot.id)
		self.assertTrue(AvailabilitySlot.objects.get(pk=self.slot.id).is_booked)

	def test_assigned_professional_can_accept_and_complete_booking(self):
		booking = Booking.objects.create(
			customer=self.customer,
			professional=self.professional,
			professional_service=self.professional_service,
			address=self.address,
			booking_type=Booking.BookingType.SCHEDULED,
			status=Booking.Status.PENDING_ACCEPT,
			service_price="125.00",
			scheduled_time="2030-01-01T18:00:00Z",
		)
		self.client.force_authenticate(user=self.professional.user)
		response = self.client.post(reverse("booking-accept", args=[booking.id]), {}, format="json")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["status"], Booking.Status.CONFIRMED)
		response = self.client.post(reverse("booking-left", args=[booking.id]), {}, format="json")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["status"], Booking.Status.LEFT)
		response = self.client.post(
			reverse("booking-reached", args=[booking.id]),
			{"latitude": str(self.address.latitude), "longitude": str(self.address.longitude)},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["status"], Booking.Status.REACHED)

		for action, expected in [("start", Booking.Status.STARTED), ("complete", Booking.Status.COMPLETED)]:
			response = self.client.post(reverse(f"booking-{action}", args=[booking.id]), {}, format="json")
			self.assertEqual(response.status_code, status.HTTP_200_OK)
			self.assertEqual(response.data["status"], expected)

		self.client.force_authenticate(user=self.customer)
		response = self.client.post(reverse("booking-confirm-complete", args=[booking.id]), {}, format="json")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["status"], Booking.Status.CONFIRMED_COMPLETE)

	@override_settings(GPS_ARRIVAL_THRESHOLD_METERS=100)
	def test_reached_requires_gps_inside_configured_radius(self):
		booking = Booking.objects.create(
			customer=self.customer,
			professional=self.professional,
			professional_service=self.professional_service,
			address=self.address,
			booking_type=Booking.BookingType.SCHEDULED,
			status=Booking.Status.CONFIRMED,
			service_price="125.00",
		)
		self.client.force_authenticate(user=self.professional.user)
		left = self.client.post(reverse("booking-left", args=[booking.id]), {}, format="json")
		self.assertEqual(left.status_code, status.HTTP_200_OK)
		outside = self.client.post(
			reverse("booking-reached", args=[booking.id]),
			{"latitude": "51.0500", "longitude": "-114.0719"},
			format="json",
		)
		self.assertEqual(outside.status_code, status.HTTP_409_CONFLICT)
		inside = self.client.post(
			reverse("booking-reached", args=[booking.id]),
			{"latitude": "51.0447", "longitude": "-114.0719"},
			format="json",
		)
		self.assertEqual(inside.status_code, status.HTTP_200_OK)
		self.assertEqual(inside.data["status"], Booking.Status.REACHED)

	def test_customer_cannot_book_at_another_customers_address(self):
		response = self.client.post(
			reverse("booking-list"),
			{
				"professional_service": self.professional_service.id,
				"address": self.other_address.id,
				"booking_type": "INSTANT",
			},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_instant_booking_rejects_scheduled_time(self):
		response = self.client.post(
			reverse("booking-list"),
			{
				"professional_service": self.professional_service.id,
				"address": self.address.id,
				"booking_type": "INSTANT",
				"scheduled_time": "2030-01-01T18:00:00Z",
			},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_instant_booking_does_not_assign_a_professional_with_active_instant_booking(self):
		self.professional.is_online = True
		self.professional.save(update_fields=["is_online"])
		Booking.objects.create(
			customer=self.other_customer,
			professional=self.professional,
			professional_service=self.professional_service,
			address=self.other_address,
			booking_type=Booking.BookingType.INSTANT,
			status=Booking.Status.PENDING_ACCEPT,
			service_price="125.00",
		)

		response = self.client.post(
			reverse("booking-list"),
			{
				"professional_service": self.professional_service.id,
				"address": self.address.id,
				"booking_type": "INSTANT",
			},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data["status"], Booking.Status.NO_MATCH)
		self.assertIsNone(response.data["professional"])

	def test_only_professional_can_create_availability(self):
		response = self.client.post(
			reverse("availability-list"),
			{
				"start_time": "2030-01-02T17:00:00Z",
				"end_time": "2030-01-02T20:00:00Z",
			},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

		self.client.force_authenticate(user=self.professional.user)
		response = self.client.post(
			reverse("availability-list"),
			{
				"start_time": "2030-01-02T17:00:00Z",
				"end_time": "2030-01-02T20:00:00Z",
			},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data["professional"], self.professional.id)
