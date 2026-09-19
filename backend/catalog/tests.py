from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import ProfessionalProfile, User

from .models import Category, MarketplaceSettings, ProfessionalService, Service, SubCategory


class ProfessionalServiceManagementTests(APITestCase):
    def setUp(self):
        self.professional_user = User.objects.create_user(
            username="pro@example.com", password="strong-password-123",
            role=User.Role.PROFESSIONAL, date_of_birth=date(1985, 1, 1),
        )
        self.customer = User.objects.create_user(
            username="customer@example.com", password="strong-password-123",
            role=User.Role.CUSTOMER, date_of_birth=date(1990, 1, 1),
        )
        ProfessionalProfile.objects.create(user=self.professional_user)
        category = Category.objects.create(name="Hair", slug="hair")
        subcategory = SubCategory.objects.create(category=category, name="Cuts", slug="cuts")
        self.service = Service.objects.create(subcategory=subcategory, name="Haircut", is_active=True)

    def test_professional_can_create_own_service_configuration(self):
        self.client.force_authenticate(user=self.professional_user)
        response = self.client.post(
            reverse("professional-manage-service-list"),
            {"service": self.service.id, "price": "50.00", "duration_minutes": 30, "is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ProfessionalService.objects.filter(professional__user=self.professional_user).exists())

    def test_customer_cannot_manage_professional_services(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(reverse("professional-manage-service-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])
        response = self.client.post(
            reverse("professional-manage-service-list"),
            {"service": self.service.id, "price": "50.00", "duration_minutes": 30, "is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MarketplaceSettingsBehaviorTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin@example.com", password="strong-password-123",
            role=User.Role.ADMIN, date_of_birth=date(1980, 1, 1), is_staff=True,
        )
        self.customer = User.objects.create_user(
            username="settings-customer@example.com", password="strong-password-123",
            role=User.Role.CUSTOMER, date_of_birth=date(1990, 1, 1),
        )

    def test_admin_can_update_settings_and_audit_log_is_created(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(reverse("marketplace-settings"), {"commission_percent": 25, "reason": "Pricing review"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(MarketplaceSettings.current().commission_percent, 25)
        self.assertEqual(MarketplaceSettings.current().audit_entries.count(), 1)

    def test_non_admin_cannot_update_settings(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.patch(reverse("marketplace-settings"), {"commission_percent": 25}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_service_duration(self):
        category = Category.objects.create(name="Nails", slug="nails")
        subcategory = SubCategory.objects.create(category=category, name="Care", slug="care")
        service = Service.objects.create(subcategory=subcategory, name="Manicure", duration_minutes=60)
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(reverse("admin-catalog"), {"service_id": service.id, "duration_minutes": 90}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        service.refresh_from_db()
        self.assertEqual(service.duration_minutes, 90)
