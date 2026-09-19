from datetime import timedelta
from math import asin, cos, radians, sin, sqrt

from django.db.models import Count, Q
from urllib.parse import urlencode
from urllib.request import urlopen
import json
from django.utils import timezone
from rest_framework import generics, permissions, serializers, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from django.conf import settings
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Address, ProfessionalProfile, User
from bookings.models import AvailabilitySlot, Booking
from catalog.models import MarketplaceSettings, MarketplaceSettingsAudit
from .serializers import (
    AddressSerializer,
    ProfessionalProfileSerializer,
    RegisterSerializer,
    UserSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)


def _address_component(components, *component_types):
    for component in components:
        if set(component.get("types", [])).intersection(component_types):
            return component.get("long_name", "")
    return ""


def _location_fields(components):
    return {
        "city": _address_component(
            components,
            "locality",
            "postal_town",
            "administrative_area_level_2",
            "sublocality",
        ),
        "province": _address_component(components, "administrative_area_level_1"),
}


def _google_error(payload, fallback):
    if payload.get("status") == "REQUEST_DENIED":
        return Response(
            {"detail": payload.get("error_message", fallback)},
            status=503,
        )
    return Response({"detail": fallback}, status=422)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        token, _ = Token.objects.get_or_create(user_id=response.data["id"])
        response.data["token"] = token.key
        return response


class LoginView(ObtainAuthToken):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        username = str(data.get("username", "")).strip()
        user = User.objects.filter(email__iexact=username).first() if "@" in username else None
        data["username"] = user.username if user else username
        serializer = AuthTokenSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        response = Response({"token": token.key})
        response.data.update(UserSerializer(user).data)
        return response


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=204)


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"configured": bool(settings.GOOGLE_CLIENT_ID)})

    def post(self, request):
        credential = str(request.data.get("credential", "")).strip()
        role = str(request.data.get("role", User.Role.CUSTOMER)).upper()
        if role not in {User.Role.CUSTOMER, User.Role.PROFESSIONAL}:
            return Response({"role": "Google signup supports customer or professional accounts."}, status=400)
        if not settings.GOOGLE_CLIENT_ID:
            return Response({"detail": "Google OAuth is not configured for this environment."}, status=503)
        if not credential:
            return Response({"credential": "Google ID token is required."}, status=400)

        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token

            payload = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except Exception:
            return Response({"detail": "Google sign-in could not be verified."}, status=401)

        email = str(payload.get("email", "")).strip().lower()
        if not email or not payload.get("email_verified"):
            return Response({"detail": "Google account email must be verified."}, status=400)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "first_name": payload.get("given_name", ""),
                "last_name": payload.get("family_name", ""),
                "role": role,
                "date_of_birth": "1900-01-01",
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
            if role == User.Role.PROFESSIONAL:
                ProfessionalProfile.objects.get_or_create(user=user)
        if not user.is_active:
            return Response({"detail": "This account is disabled."}, status=403)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, **UserSerializer(user).data})


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "If that email is registered, a reset link has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password reset successfully."})


class ReverseGeocodeView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")
        if not latitude or not longitude:
            return Response({"detail": "Latitude and longitude are required."}, status=400)
        if not settings.GOOGLE_MAPS_API_KEY or not settings.GOOGLE_MAPS_API_BASE_URL:
            return Response({"detail": "Location lookup is not configured. Enter a city manually."}, status=503)
        query = urlencode({"latlng": f"{latitude},{longitude}", "key": settings.GOOGLE_MAPS_API_KEY})
        try:
            with urlopen(f"{settings.GOOGLE_MAPS_API_BASE_URL.rstrip('/')}/maps/api/geocode/json?{query}", timeout=5) as result:
                payload = json.load(result)
        except (OSError, ValueError):
            return Response({"detail": "Location lookup is temporarily unavailable."}, status=502)
        if payload.get("status") != "OK" or not payload.get("results"):
            return _google_error(payload, "We could not identify that location.")
        result = payload["results"][0]
        components = result.get("address_components", [])
        return Response({"formatted_address": result.get("formatted_address", ""), **_location_fields(components)})


class PlacesAutocompleteView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = str(request.query_params.get("input", "")).strip()
        if len(query) < 2:
            return Response({"predictions": []})
        if not settings.GOOGLE_MAPS_API_KEY or not settings.GOOGLE_MAPS_API_BASE_URL or settings.GOOGLE_MAPS_API_KEY.startswith("replace-with"):
            return Response({"detail": "Location autocomplete is not configured."}, status=503)
        params = urlencode({"input": query, "key": settings.GOOGLE_MAPS_API_KEY, "components": "country:ca"})
        try:
            with urlopen(f"{settings.GOOGLE_MAPS_API_BASE_URL.rstrip('/')}/maps/api/place/autocomplete/json?{params}", timeout=5) as result:
                payload = json.load(result)
        except (OSError, ValueError):
            return Response({"detail": "Location autocomplete is temporarily unavailable."}, status=502)
        if payload.get("status") not in {"OK", "ZERO_RESULTS"}:
            return _google_error(payload, "Location autocomplete is unavailable.")
        return Response({
            "predictions": [
                {"place_id": item.get("place_id"), "description": item.get("description")}
                for item in payload.get("predictions", [])
            ]
        })


class AddressGeocodeView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        address = str(request.query_params.get("address", "")).strip()
        if len(address) < 5:
            return Response({"detail": "Enter a complete service address."}, status=400)
        if not settings.GOOGLE_MAPS_API_KEY or not settings.GOOGLE_MAPS_API_BASE_URL or settings.GOOGLE_MAPS_API_KEY.startswith("replace-with"):
            return Response({"detail": "Address geocoding is not configured."}, status=503)
        params = urlencode({"address": address, "key": settings.GOOGLE_MAPS_API_KEY, "region": "ca"})
        try:
            with urlopen(f"{settings.GOOGLE_MAPS_API_BASE_URL.rstrip('/')}/maps/api/geocode/json?{params}", timeout=5) as result:
                payload = json.load(result)
        except (OSError, ValueError):
            return Response({"detail": "Address geocoding is temporarily unavailable."}, status=502)
        results = payload.get("results") or []
        if payload.get("status") != "OK" or not results:
            return _google_error(payload, "We could not identify that address.")
        result = results[0]
        location = result.get("geometry", {}).get("location", {})
        if not location:
            return Response({"detail": "We could not identify that address."}, status=422)
        components = result.get("address_components", [])
        location_fields = _location_fields(components)
        return Response({
            "formatted_address": result.get("formatted_address", address),
            **location_fields,
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
        })


class PlaceDetailsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        place_id = str(request.query_params.get("place_id", "")).strip()
        if not place_id or not settings.GOOGLE_MAPS_API_KEY or not settings.GOOGLE_MAPS_API_BASE_URL or settings.GOOGLE_MAPS_API_KEY.startswith("replace-with"):
            return Response({"detail": "Location details are not configured."}, status=503)
        params = urlencode({"place_id": place_id, "fields": "formatted_address,geometry,address_components", "key": settings.GOOGLE_MAPS_API_KEY})
        try:
            with urlopen(f"{settings.GOOGLE_MAPS_API_BASE_URL.rstrip('/')}/maps/api/place/details/json?{params}", timeout=5) as result:
                payload = json.load(result)
        except (OSError, ValueError):
            return Response({"detail": "Location details are temporarily unavailable."}, status=502)
        result = payload.get("result", {})
        location = result.get("geometry", {}).get("location", {})
        if payload.get("status") != "OK" or not location:
            return _google_error(payload, "We could not identify that location.")
        components = result.get("address_components", [])
        return Response({"formatted_address": result.get("formatted_address", ""), **_location_fields(components), "latitude": location.get("lat"), "longitude": location.get("lng"), "place_id": place_id})


class AdminDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return Response({"detail": "Administrator access required."}, status=403)

        from bookings.models import Booking
        from bookings.serializers import BookingSerializer
        from catalog.models import Category, ProfessionalService, Service
        from payments.models import PaymentAuthorization
        from reviews.models import Review
        from verification.models import ProfessionalVerification

        bookings = Booking.objects.select_related("customer", "professional", "professional__user").order_by("-created_at")
        return Response({
            "counts": {
                "customers": User.objects.filter(role=User.Role.CUSTOMER).count(),
                "professionals": ProfessionalProfile.objects.count(),
                "active_professionals": ProfessionalProfile.objects.filter(is_active=True).count(),
                "bookings": bookings.count(),
                "today_bookings": bookings.filter(created_at__date=timezone.now().date()).count(),
                "completed_bookings": bookings.filter(status=Booking.Status.CONFIRMED_COMPLETE).count(),
                "cancelled_bookings": bookings.filter(status__in=[Booking.Status.CANCELLED_CUSTOMER, Booking.Status.CANCELLED_PROFESSIONAL]).count(),
                "pending_verifications": ProfessionalVerification.objects.filter(status=ProfessionalVerification.Status.PENDING).count(),
                "services": Service.objects.filter(is_active=True).count(),
                "categories": Category.objects.filter(is_active=True).count(),
                "reviews": Review.objects.count(),
                "payments": PaymentAuthorization.objects.count(),
                "pending_payments": PaymentAuthorization.objects.filter(status=PaymentAuthorization.Status.AUTHORIZED).count(),
            },
            "recent_bookings": BookingSerializer(bookings[:10], many=True, context={"request": request}).data,
            "popular_services": list(ProfessionalService.objects.values("service__name").annotate(total=Count("bookings")).order_by("-total")[:5]),
        })


class MarketplaceSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    fields = [
        "instant_initial_radius_km", "instant_max_radius_km", "scheduled_search_radius_km",
        "radius_expansion_step_km", "professional_service_radius_km", "maximum_travel_distance_km",
        "included_travel_distance_km", "travel_fee_per_km", "maximum_travel_fee", "minimum_booking_price",
        "commission_percent", "fixed_platform_fee", "minimum_platform_fee", "maximum_platform_fee", "customer_cancellation_window_minutes",
        "professional_acceptance_window_minutes", "scheduled_minimum_notice_minutes",
        "maximum_advance_booking_days", "instant_booking_timeout_minutes", "rematching_timeout_minutes", "reminder_minutes_before_booking", "rematching_enabled",
        "instant_booking_enabled", "scheduled_booking_enabled", "multiple_service_booking_enabled",
        "travel_fees_enabled", "availability_weight", "distance_weight", "rating_weight",
        "review_count_weight", "experience_weight", "reliability_weight", "tax_enabled", "tax_name", "tax_percent",
    ]

    def _require_admin(self, request):
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            raise PermissionDenied("Administrator access required.")

    def get(self, request):
        self._require_admin(request)
        settings_object = MarketplaceSettings.current()
        return Response({field: getattr(settings_object, field) for field in self.fields})

    def patch(self, request):
        self._require_admin(request)
        settings_object = MarketplaceSettings.current()
        changes = {}
        for field in self.fields:
            if field in request.data and request.data[field] != getattr(settings_object, field):
                changes[field] = {"previous": str(getattr(settings_object, field)), "new": str(request.data[field])}
                setattr(settings_object, field, request.data[field])
        try:
            settings_object.full_clean()
        except serializers.ValidationError:
            raise
        except Exception as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else str(exc)) from exc
        settings_object.save()
        if changes:
            MarketplaceSettingsAudit.objects.create(
                settings=settings_object,
                admin=request.user,
                changes=changes,
                reason=str(request.data.get("reason", ""))[:255],
            )
        return Response({field: getattr(settings_object, field) for field in self.fields})


class ProfessionalDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != User.Role.PROFESSIONAL:
            return Response({"detail": "Professional access required."}, status=403)
        from bookings.models import Booking
        from bookings.serializers import BookingSerializer

        profile = ProfessionalProfile.objects.select_related("user", "base_address").get(user=request.user)
        bookings = Booking.objects.filter(professional=profile).select_related(
            "customer", "professional_service", "professional_service__service", "address"
        ).prefetch_related("status_events").order_by("scheduled_time", "-created_at")
        return Response({
            "profile": ProfessionalProfileSerializer(profile, context={"request": request}).data,
            "bookings": BookingSerializer(bookings, many=True, context={"request": request}).data,
        })


class ProfessionalStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != User.Role.PROFESSIONAL:
            return Response({"detail": "Professional access required."}, status=403)
        profile = ProfessionalProfile.objects.get(user=request.user)
        if not profile.is_active:
            return Response({"detail": "Your profile must be verified before going online."}, status=409)
        profile.is_online = bool(request.data.get("is_online", False))
        profile.save(update_fields=["is_online"])
        return Response({"is_online": profile.is_online})


class ProfessionalProfileManageView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfessionalProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        if self.request.user.role != User.Role.PROFESSIONAL:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Professional access required.")
        return ProfessionalProfile.objects.get(user=self.request.user)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by("-is_default", "-created_at")


class ProfessionalProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProfessionalProfileSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = (
            ProfessionalProfile.objects.select_related("user", "base_address")
            .filter(is_active=True)
            .order_by("-is_online", "-average_rating", "-review_count")
        )

        available_now = self.request.query_params.get("available_now")
        if available_now in {"1", "true", "yes"}:
            queryset = queryset.filter(is_online=True)

        query = self.request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(bio__icontains=query)
                | Q(services_offered__service__name__icontains=query)
            ).distinct()

        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(services_offered__service__subcategory__category__slug=category).distinct()

        service = self.request.query_params.get("service")
        if service:
            queryset = queryset.filter(services_offered__service_id=service).distinct()

        service_slug = self.request.query_params.get("service_slug")
        if service_slug:
            queryset = queryset.filter(services_offered__service__slug=service_slug).distinct()

        audience = self.request.query_params.get("audience")
        if audience:
            queryset = queryset.filter(services_offered__service__subcategory__audience=audience.upper()).distinct()

        city = self.request.query_params.get("city")
        if city:
            queryset = queryset.filter(service_cities__icontains=city)

        minimum_rating = self.request.query_params.get("min_rating")
        if minimum_rating:
            queryset = queryset.filter(average_rating__gte=minimum_rating)

        minimum_price = self.request.query_params.get("min_price")
        if minimum_price:
            queryset = queryset.filter(services_offered__price__gte=minimum_price).distinct()

        maximum_price = self.request.query_params.get("max_price")
        if maximum_price:
            queryset = queryset.filter(services_offered__price__lte=maximum_price).distinct()

        ordering = self.request.query_params.get("ordering")
        if ordering in {"rating", "-rating", "experience", "-experience"}:
            field = {"rating": "average_rating", "-rating": "-average_rating", "experience": "years_experience", "-experience": "-years_experience"}[ordering]
            queryset = queryset.order_by(field, "-review_count")
        elif ordering in {"price", "-price"}:
            prefix = "-" if ordering.startswith("-") else ""
            queryset = queryset.order_by(f"{prefix}services_offered__price")

        latitude = self.request.query_params.get("latitude")
        longitude = self.request.query_params.get("longitude")
        booking_type = self.request.query_params.get("booking_type", "").upper()
        requested_datetime = self._requested_datetime()
        if latitude is None or longitude is None:
            if booking_type == "SCHEDULED" and requested_datetime:
                service_id = self.request.query_params.get("service")
                service_slug = self.request.query_params.get("service_slug")
                available_ids = []
                for professional in queryset.prefetch_related("services_offered__service"):
                    matching_services = [
                        item for item in professional.services_offered.all()
                        if item.is_active
                        and (not service_id or str(item.service_id) == service_id)
                        and (not service_slug or item.service.slug == service_slug)
                        and (not audience or item.service.subcategory.audience == audience.upper())
                    ]
                    if matching_services and self._is_available(
                        professional,
                        booking_type,
                        requested_datetime,
                        matching_services[0].duration_minutes,
                    ):
                        available_ids.append(professional.id)
                return queryset.filter(id__in=available_ids)
            return queryset
        try:
            customer_latitude = float(latitude)
            customer_longitude = float(longitude)
        except (TypeError, ValueError):
            return queryset.none()

        marketplace_settings = MarketplaceSettings.current()
        service_id = self.request.query_params.get("service")
        service_slug = self.request.query_params.get("service_slug")
        candidates = []
        for professional in queryset.prefetch_related("services_offered__service"):
            if not professional.base_address:
                continue
            distance_km = self._distance_km(
                customer_latitude,
                customer_longitude,
                float(professional.base_address.latitude),
                float(professional.base_address.longitude),
            )
            radius = float(marketplace_settings.scheduled_search_radius_km)
            if booking_type == "INSTANT":
                radius = float(marketplace_settings.instant_max_radius_km)
            radius = min(radius, float(professional.service_radius_km), float(marketplace_settings.maximum_travel_distance_km))
            if distance_km > radius:
                continue
            matching_services = [
                item for item in professional.services_offered.all()
                if item.is_active
                and (not service_id or str(item.service_id) == service_id)
                and (not service_slug or item.service.slug == service_slug)
                and (not audience or item.service.subcategory.audience == audience.upper())
            ]
            if not matching_services:
                continue
            available = self._is_available(professional, booking_type, requested_datetime, matching_services[0].duration_minutes)
            if booking_type == "INSTANT" and (not professional.is_online or not available):
                continue
            if booking_type == "SCHEDULED" and requested_datetime and not available:
                continue
            professional._search_distance_km = distance_km
            candidates.append(professional)

        if booking_type == "INSTANT":
            initial_candidates = [
                professional for professional in candidates
                if professional._search_distance_km <= float(marketplace_settings.instant_initial_radius_km)
            ]
            candidates = initial_candidates or [
                professional for professional in candidates
                if professional._search_distance_km <= float(marketplace_settings.instant_max_radius_km)
            ]

        return sorted(
            candidates,
            key=lambda professional: (
                professional._search_distance_km,
                -float(professional.average_rating or 0),
                -professional.review_count,
                -professional.years_experience,
            ),
        )

    def _requested_datetime(self):
        value = self.request.query_params.get("scheduled_time")
        if not value:
            return None
        from django.utils.dateparse import parse_datetime

        requested_datetime = parse_datetime(value)
        if requested_datetime and timezone.is_naive(requested_datetime):
            requested_datetime = timezone.make_aware(requested_datetime)
        return requested_datetime

    @staticmethod
    def _distance_km(first_latitude, first_longitude, second_latitude, second_longitude):
        latitude_delta = radians(second_latitude - first_latitude)
        longitude_delta = radians(second_longitude - first_longitude)
        first_latitude = radians(first_latitude)
        second_latitude = radians(second_latitude)
        value = sin(latitude_delta / 2) ** 2 + cos(first_latitude) * cos(second_latitude) * sin(longitude_delta / 2) ** 2
        return 6371 * 2 * asin(sqrt(value))

    @staticmethod
    def _is_available(professional, booking_type, requested_datetime, duration):
        start_time = requested_datetime or timezone.now()
        end_time = start_time + timedelta(minutes=duration)
        if booking_type == "SCHEDULED" and not AvailabilitySlot.objects.filter(
            professional=professional,
            is_booked=False,
            start_time__lte=start_time,
            end_time__gte=end_time,
        ).exists():
            return False
        return not Booking.objects.filter(
            professional=professional,
            scheduled_time__lt=end_time,
            scheduled_time__gte=start_time - timedelta(minutes=duration),
        ).exclude(
            status__in=[
                Booking.Status.CANCELLED_CUSTOMER,
                Booking.Status.CANCELLED_PROFESSIONAL,
                Booking.Status.NO_MATCH,
                Booking.Status.CONFIRMED_COMPLETE,
            ]
        ).exists()
