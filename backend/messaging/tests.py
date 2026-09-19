from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Address, ProfessionalProfile, User
from bookings.models import Booking
from catalog.models import Category, ProfessionalService, Service, SubCategory

from .models import Conversation, Message


class BookingChatTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="chat-customer", password="test-password-123", role=User.Role.CUSTOMER, date_of_birth=date(1990, 1, 1))
        professional_user = User.objects.create_user(username="chat-pro", password="test-password-123", role=User.Role.PROFESSIONAL, date_of_birth=date(1985, 1, 1))
        outsider = User.objects.create_user(username="chat-outsider", password="test-password-123", role=User.Role.CUSTOMER, date_of_birth=date(1990, 1, 1))
        self.outsider = outsider
        professional = ProfessionalProfile.objects.create(user=professional_user, is_active=True)
        address = Address.objects.create(user=self.customer, full_address="Calgary", latitude="51.0447", longitude="-114.0719")
        category = Category.objects.create(name="Hair", slug="hair")
        subcategory = SubCategory.objects.create(category=category, name="Cuts", slug="cuts")
        service = Service.objects.create(subcategory=subcategory, name="Haircut")
        professional_service = ProfessionalService.objects.create(professional=professional, service=service, price="50.00", duration_minutes=45)
        booking = Booking.objects.create(customer=self.customer, professional=professional, professional_service=professional_service, address=address, booking_type=Booking.BookingType.INSTANT, status=Booking.Status.CONFIRMED, service_price="50.00")
        self.conversation = Conversation.objects.create(booking=booking)

    def test_participants_can_read_and_send_but_outsider_cannot(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(reverse("conversation-send", args=[self.conversation.id]), {"body": "Hello"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(reverse("conversation-detail", args=[self.conversation.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.post(reverse("conversation-send", args=[self.conversation.id]), {"body": "Intrusion"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
