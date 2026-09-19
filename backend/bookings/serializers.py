from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from math import asin, cos, radians, sin, sqrt

from django.conf import settings as django_settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from accounts.models import Address, User
from catalog.models import MarketplaceSettings, ProfessionalService

from .models import AvailabilitySlot, Booking, BookingDecline, BookingNotification, BookingService, BookingStatusEvent


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilitySlot
        fields = ["id", "professional", "start_time", "end_time", "is_booked"]
        read_only_fields = ["id", "professional", "is_booked"]

    def validate(self, attrs):
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return attrs


class BookingStatusEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingStatusEvent
        fields = ["id", "status", "occurred_at", "note"]


class BookingDeclineSerializer(serializers.ModelSerializer):
    professional_name = serializers.CharField(
        source="professional.user.get_full_name",
        read_only=True,
    )

    class Meta:
        model = BookingDecline
        fields = ["id", "professional", "professional_name", "reason", "declined_at"]


class BookingNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingNotification
        fields = ["id", "booking", "event", "body", "read_at", "created_at"]
        read_only_fields = fields


class BookingSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    status_events = BookingStatusEventSerializer(many=True, read_only=True)
    declines = BookingDeclineSerializer(many=True, read_only=True)
    professional_name = serializers.CharField(source="professional.user.get_full_name", read_only=True, allow_null=True)
    service_name = serializers.CharField(source="professional_service.service.name", read_only=True)
    service_category = serializers.CharField(source="professional_service.service.subcategory.category.name", read_only=True)
    address_label = serializers.CharField(source="address.label", read_only=True)
    address_full = serializers.CharField(source="address.full_address", read_only=True)
    selected_service_ids = serializers.PrimaryKeyRelatedField(
        source="selected_services_input",
        queryset=ProfessionalService.objects.filter(is_active=True),
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = Booking
        fields = [
            "id",
            "customer",
            "professional",
            "professional_service",
            "professional_name",
            "service_name",
            "service_category",
            "availability_slot",
            "address",
            "address_label",
            "address_full",
            "booking_type",
            "status",
            "service_price",
            "duration_minutes",
            "travel_fee",
            "priority_fee",
            "platform_commission",
            "scheduled_time",
            "reaffirmation_confirmed_by_customer",
            "reaffirmation_confirmed_by_professional",
            "reached_latitude",
            "reached_longitude",
            "before_after_consent",
            "total_amount",
            "created_at",
            "updated_at",
            "left_at",
            "reached_at",
            "started_at",
            "completed_at",
            "confirmed_complete_at",
            "status_events",
            "declines",
            "selected_service_ids",
        ]
        read_only_fields = [
            "id",
            "customer",
            "professional",
            "status",
            "service_price",
            "duration_minutes",
            "travel_fee",
            "platform_commission",
            "reaffirmation_confirmed_by_customer",
            "reaffirmation_confirmed_by_professional",
            "reached_latitude",
            "reached_longitude",
            "created_at",
            "updated_at",
            "left_at",
            "reached_at",
            "started_at",
            "completed_at",
            "confirmed_complete_at",
            "status_events",
            "declines",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        if request.user.role != User.Role.CUSTOMER:
            raise serializers.ValidationError("Only customer accounts can create bookings.")

        professional_service = attrs["professional_service"]
        selected_services = attrs.pop("selected_services_input", None) or [professional_service]
        if professional_service not in selected_services:
            selected_services.insert(0, professional_service)
        if not MarketplaceSettings.current().multiple_service_booking_enabled and len(selected_services) > 1:
            raise serializers.ValidationError("Multiple-service bookings are currently disabled.")
        if any(item.professional_id != professional_service.professional_id for item in selected_services):
            raise serializers.ValidationError("All selected services must belong to the same professional.")
        attrs["selected_services_input"] = selected_services
        if not professional_service.is_active or not professional_service.professional.is_active:
            raise serializers.ValidationError("This professional service is not available.")

        booking_type = attrs["booking_type"]
        scheduled_time = attrs.get("scheduled_time")

        if booking_type == Booking.BookingType.SCHEDULED and scheduled_time is None:
            raise serializers.ValidationError("Scheduled bookings require a scheduled_time.")

        if booking_type == Booking.BookingType.INSTANT and scheduled_time is not None:
            raise serializers.ValidationError("Instant bookings cannot include a scheduled_time.")

        if booking_type == Booking.BookingType.SCHEDULED and scheduled_time <= timezone.now():
            raise serializers.ValidationError("Scheduled bookings must be in the future.")

        if booking_type == Booking.BookingType.SCHEDULED:
            marketplace_settings = MarketplaceSettings.current()
            if scheduled_time > timezone.now() + timedelta(days=marketplace_settings.maximum_advance_booking_days):
                raise serializers.ValidationError("That date is beyond the maximum advance booking window.")
            if scheduled_time < timezone.now() + timedelta(minutes=marketplace_settings.scheduled_minimum_notice_minutes):
                raise serializers.ValidationError("More notice is required for scheduled bookings.")

        if attrs["address"].user_id != request.user.id:
            raise serializers.ValidationError("Bookings must use one of your saved addresses.")

        total_duration = sum(item.duration_minutes for item in selected_services)
        if booking_type == Booking.BookingType.SCHEDULED and attrs.get("availability_slot") is not None:
            slot = attrs["availability_slot"]
            if slot.professional_id != professional_service.professional_id:
                raise serializers.ValidationError("The selected slot belongs to another professional.")
            if slot.is_booked:
                raise serializers.ValidationError("That availability slot is already booked.")
            if scheduled_time < slot.start_time or scheduled_time + timedelta(minutes=total_duration) > slot.end_time:
                raise serializers.ValidationError("The service does not fit inside the selected slot.")

        if booking_type == Booking.BookingType.INSTANT and attrs.get("availability_slot") is not None:
            raise serializers.ValidationError("Instant bookings cannot reserve a scheduled slot.")

        if booking_type == Booking.BookingType.SCHEDULED and attrs.get("availability_slot") is None:
            slot_exists = AvailabilitySlot.objects.filter(
                professional=professional_service.professional,
                is_booked=False,
                start_time__lte=scheduled_time,
                end_time__gte=scheduled_time + timedelta(minutes=total_duration),
            ).exists()
            if not slot_exists:
                raise serializers.ValidationError("No open availability slot can fit this service time.")

        return attrs

    @staticmethod
    def _distance_km(first_latitude, first_longitude, second_latitude, second_longitude):
        earth_radius_km = 6371
        latitude_delta = radians(float(second_latitude) - float(first_latitude))
        longitude_delta = radians(float(second_longitude) - float(first_longitude))
        first_latitude = radians(float(first_latitude))
        second_latitude = radians(float(second_latitude))
        value = sin(latitude_delta / 2) ** 2 + cos(first_latitude) * cos(second_latitude) * sin(longitude_delta / 2) ** 2
        return earth_radius_km * 2 * asin(sqrt(value))

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        professional_service: ProfessionalService = validated_data["professional_service"]
        booking_type = validated_data["booking_type"]
        selected_services = validated_data.pop("selected_services_input", [professional_service])
        marketplace_settings = MarketplaceSettings.current()

        validated_data["customer"] = request.user
        validated_data["service_price"] = sum((item.price for item in selected_services), start=professional_service.price * 0)
        validated_data["duration_minutes"] = sum(item.duration_minutes for item in selected_services)
        if professional_service.professional.base_address is None:
            raise serializers.ValidationError("This professional has no geocoded service address.")
        distance_km = self._distance_km(
            validated_data["address"].latitude,
            validated_data["address"].longitude,
            professional_service.professional.base_address.latitude,
            professional_service.professional.base_address.longitude,
        )
        if distance_km > float(min(professional_service.professional.service_radius_km, marketplace_settings.maximum_travel_distance_km)):
            raise serializers.ValidationError("This professional does not serve the selected location.")
        included_distance = float(marketplace_settings.included_travel_distance_km)
        travel_fee = max(0, distance_km - included_distance) * float(marketplace_settings.travel_fee_per_km)
        validated_data["travel_fee"] = Decimal(str(min(travel_fee, float(marketplace_settings.maximum_travel_fee)))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if marketplace_settings.travel_fees_enabled else Decimal("0.00")
        commission = (validated_data["service_price"] * marketplace_settings.commission_percent / Decimal("100")) + marketplace_settings.fixed_platform_fee
        commission = max(commission, marketplace_settings.minimum_platform_fee)
        if marketplace_settings.maximum_platform_fee:
            commission = min(commission, marketplace_settings.maximum_platform_fee)
        validated_data["platform_commission"] = commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if booking_type == Booking.BookingType.INSTANT:
            professional = professional_service.professional.__class__.objects.select_for_update().get(
                pk=professional_service.professional_id
            )
            if not professional.is_online or distance_km > float(marketplace_settings.instant_max_radius_km):
                validated_data["status"] = Booking.Status.NO_MATCH
            else:
                validated_data["professional"] = professional
                validated_data["status"] = Booking.Status.PENDING_ACCEPT
            validated_data.setdefault("priority_fee", 15)
        else:
            validated_data["status"] = Booking.Status.PENDING_ACCEPT
            validated_data["professional"] = professional_service.professional
            validated_data.setdefault("priority_fee", 0)

        if validated_data.get("professional") is not None:
            active_statuses = [
                Booking.Status.PENDING_ACCEPT,
                Booking.Status.CONFIRMED,
                Booking.Status.AWAITING_REAFFIRMATION,
                Booking.Status.LEFT,
                Booking.Status.REACHED,
                Booking.Status.STARTED,
                Booking.Status.COMPLETED,
            ]
            active_bookings = Booking.objects.select_for_update().filter(
                professional_id=validated_data["professional"].pk,
                status__in=active_statuses,
            )
            if booking_type == Booking.BookingType.INSTANT:
                has_conflict = active_bookings.filter(booking_type=Booking.BookingType.INSTANT).exists()
            else:
                requested_start = validated_data["scheduled_time"]
                requested_end = requested_start + timedelta(minutes=validated_data["duration_minutes"])
                has_conflict = any(
                    existing.scheduled_time
                    and existing.scheduled_time < requested_end
                    and requested_start < existing.scheduled_time + timedelta(minutes=existing.duration_minutes)
                    for existing in active_bookings
                )
            if has_conflict:
                if booking_type == Booking.BookingType.INSTANT:
                    validated_data["professional"] = None
                    validated_data["status"] = Booking.Status.NO_MATCH
                else:
                    raise serializers.ValidationError("This professional is already booked for that time.")

        availability_slot = validated_data.get("availability_slot")
        if booking_type == Booking.BookingType.SCHEDULED:
            slot_query = AvailabilitySlot.objects.select_for_update().filter(
                professional=professional_service.professional,
                is_booked=False,
                start_time__lte=validated_data["scheduled_time"],
                end_time__gte=validated_data["scheduled_time"] + timedelta(minutes=validated_data["duration_minutes"]),
            ).order_by("start_time")
            availability_slot = slot_query.filter(pk=availability_slot.pk).first() if availability_slot else slot_query.first()
            if availability_slot is None:
                raise serializers.ValidationError("That availability slot was just booked. Choose another time.")
            validated_data["availability_slot"] = availability_slot
        if availability_slot is not None:
            availability_slot.is_booked = True
            availability_slot.save(update_fields=["is_booked"])

        booking = super().create(validated_data)
        BookingStatusEvent.objects.create(
            booking=booking,
            status=booking.status,
            note="Booking created.",
        )
        BookingNotification.objects.create(
            booking=booking,
            recipient=booking.customer,
            event="BOOKING_REQUESTED",
            body="Your booking request was received.",
        )
        if booking.professional_id:
            from messaging.models import Conversation

            Conversation.objects.get_or_create(booking=booking)
            BookingNotification.objects.create(
                booking=booking,
                recipient=booking.professional.user,
                event="BOOKING_REQUESTED",
                body="You have a new booking request.",
            )
        for selected_service in selected_services:
            BookingService.objects.create(
                booking=booking,
                professional_service=selected_service,
                service_price=selected_service.price,
                duration_minutes=selected_service.duration_minutes,
            )
        return booking
