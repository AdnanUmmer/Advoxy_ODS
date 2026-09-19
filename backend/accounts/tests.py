from datetime import date

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from .models import ProfessionalProfile, User

from catalog.models import Category, ProfessionalService, Service, SubCategory


class AuthenticationApiTests(APITestCase):
	def test_login_normalizes_demo_email_input(self):
		User.objects.create_user(
			username="demo_customer_01@demo.advoxy.test",
			email="demo_customer_01@demo.advoxy.test",
			password="DemoOnly-Advoxy-2026!",
			role=User.Role.CUSTOMER,
			date_of_birth=date(1990, 1, 1),
		)
		response = self.client.post(
			reverse("login"),
			{"username": " Demo_Customer_01@Demo.Advoxy.Test ", "password": "DemoOnly-Advoxy-2026!"},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["email"], "demo_customer_01@demo.advoxy.test")

	def test_customer_can_register_and_login(self):
		payload = {
			"username": "new@example.com",
			"email": "new@example.com",
			"password": "strong-password-123",
			"first_name": "New",
			"last_name": "Customer",
			"phone_number": "4035550100",
			"date_of_birth": "1990-01-01",
			"role": User.Role.CUSTOMER,
		}
		registered = self.client.post(reverse("register"), payload, format="json")
		self.assertEqual(registered.status_code, status.HTTP_201_CREATED)
		self.assertTrue(registered.data["token"])

		logged_in = self.client.post(
			reverse("login"), {"username": payload["username"], "password": payload["password"]}, format="json"
		)
		self.assertEqual(logged_in.status_code, status.HTTP_200_OK)
		self.assertEqual(logged_in.data["role"], User.Role.CUSTOMER)

	def test_public_signup_cannot_create_admin(self):
		response = self.client.post(
			reverse("register"),
			{
				"username": "admin@example.com",
				"email": "admin@example.com",
				"password": "strong-password-123",
				"date_of_birth": date(1990, 1, 1),
				"role": User.Role.ADMIN,
			},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_admin_dashboard_requires_admin_role(self):
		customer = User.objects.create_user(
			username="customer@example.com", password="strong-password-123",
			role=User.Role.CUSTOMER, date_of_birth=date(1990, 1, 1),
		)
		self.client.force_authenticate(user=customer)
		response = self.client.get(reverse("admin-dashboard"))
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	@override_settings(GOOGLE_CLIENT_ID="")
	def test_google_login_requires_oauth_configuration(self):
		response = self.client.post(reverse("google-login"), {"credential": "token"}, format="json")
		self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

	@override_settings(GOOGLE_CLIENT_ID="public-client", GOOGLE_CLIENT_SECRET="private-secret")
	def test_google_configuration_only_exposes_public_client_id(self):
		self.client.credentials(HTTP_AUTHORIZATION="Token expired-token")
		response = self.client.get(reverse("google-login"))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data, {"configured": True})

	@override_settings(GOOGLE_CLIENT_ID="google-client-id")
	@patch("google.oauth2.id_token.verify_oauth2_token")
	def test_google_login_rejects_disabled_account(self, verify_token):
		user = User.objects.create_user(username="disabled@example.com", email="disabled@example.com", is_active=False, date_of_birth=date(1990, 1, 1))
		verify_token.return_value = {"email": user.email, "email_verified": True}
		response = self.client.post(reverse("google-login"), {"credential": "token"}, format="json")
		self.assertEqual(response.status_code, 403)
		self.assertFalse(hasattr(user, "auth_token"))

	@override_settings(GOOGLE_CLIENT_ID="google-client-id")
	@patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("invalid"))
	def test_google_login_rejects_invalid_token(self, verify_token):
		response = self.client.post(reverse("google-login"), {"credential": "invalid"}, format="json")
		self.assertEqual(response.status_code, 401)

	@override_settings(GOOGLE_CLIENT_ID="google-client-id")
	@patch("google.oauth2.id_token.verify_oauth2_token")
	def test_google_login_creates_customer_with_verified_google_email(self, verify_token):
		verify_token.return_value = {
			"email": "google@example.com",
			"email_verified": True,
			"given_name": "Gina",
			"family_name": "Google",
		}
		response = self.client.post(reverse("google-login"), {"credential": "token"}, format="json")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["email"], "google@example.com")
		self.assertEqual(response.data["role"], User.Role.CUSTOMER)
		self.assertTrue(response.data["token"])

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_password_reset_is_single_use(self):
		user = User.objects.create_user(
			username="reset@example.com", email="reset@example.com", password="old-password-123",
			role=User.Role.CUSTOMER, date_of_birth=date(1990, 1, 1),
		)
		request = self.client.post(reverse("password-reset-request"), {"email": user.email}, format="json")
		self.assertEqual(request.status_code, status.HTTP_200_OK)
		self.assertEqual(len(mail.outbox), 1)
		message = mail.outbox[0].body
		token = message.split("token=")[1].strip()

		confirmed = self.client.post(
			reverse("password-reset-confirm"),
			{"uid": user.id, "token": token, "new_password": "new-password-123"},
			format="json",
		)
		self.assertEqual(confirmed.status_code, status.HTTP_200_OK)
		reused = self.client.post(
			reverse("password-reset-confirm"),
			{"uid": user.id, "token": token, "new_password": "another-password-123"},
			format="json",
		)
		self.assertEqual(reused.status_code, status.HTTP_400_BAD_REQUEST)

	def test_professional_search_is_filtered_and_paginated(self):
		professional_user = User.objects.create_user(
			username="maya@example.com", first_name="Maya", last_name="Laurent",
			password="strong-password-123", role=User.Role.PROFESSIONAL, date_of_birth=date(1985, 1, 1),
		)
		profile = ProfessionalProfile.objects.create(user=professional_user)
		profile.is_active = True
		profile.bio = "Colour specialist"
		profile.save(update_fields=["is_active", "bio"])
		category = Category.objects.create(name="Hair", slug="hair")
		subcategory = SubCategory.objects.create(category=category, name="Colour", slug="colour")
		service = Service.objects.create(subcategory=subcategory, name="Balayage")
		ProfessionalService.objects.create(professional=profile, service=service, price="120.00", duration_minutes=90)

		response = self.client.get(reverse("professional-list"), {"q": "balayage", "page": 1})
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["count"], 1)
		self.assertEqual(response.data["results"][0]["display_name"], "Maya Laurent")
