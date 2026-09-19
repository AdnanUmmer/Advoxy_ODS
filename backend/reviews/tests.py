from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Address, ProfessionalProfile, User
from bookings.models import Booking
from catalog.models import Category, ProfessionalService, Service, SubCategory


class ReviewApiTests(APITestCase):
	def setUp(self):
		self.customer = User.objects.create_user(
			username="reviewer@example.com", password="strong-password-123",
			role=User.Role.CUSTOMER, date_of_birth=date(1990, 1, 1),
		)
		professional_user = User.objects.create_user(
			username="reviewee@example.com", password="strong-password-123",
			role=User.Role.PROFESSIONAL, date_of_birth=date(1985, 1, 1),
			first_name="Maya", last_name="Pro",
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
			status=Booking.Status.CONFIRMED_COMPLETE, service_price="100.00",
		)
		self.client.force_authenticate(user=self.customer)

	def test_customer_can_review_completed_booking_once(self):
		response = self.client.post(
			reverse("review-list"),
			{"booking": self.booking.id, "rating": 5, "comment": "Excellent."},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		duplicate = self.client.post(
			reverse("review-list"),
			{"booking": self.booking.id, "rating": 4, "comment": "Second review."},
			format="json",
		)
		self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)

	def test_customer_cannot_review_incomplete_booking(self):
		self.booking.status = Booking.Status.STARTED
		self.booking.save(update_fields=["status"])
		response = self.client.post(
			reverse("review-list"),
			{"booking": self.booking.id, "rating": 5},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
