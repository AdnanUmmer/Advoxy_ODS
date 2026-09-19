from datetime import timedelta
from math import asin, cos, radians, sin, sqrt

from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework import decorators, permissions, response, status, viewsets
from rest_framework.exceptions import PermissionDenied

from catalog.models import MarketplaceSettings

from .models import AvailabilitySlot, Booking, BookingDecline, BookingNotification, BookingStatusEvent
from .serializers import AvailabilitySlotSerializer, BookingNotificationSerializer, BookingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = (
            Booking.objects.select_related(
                "customer",
                "professional",
                "professional__user",
                "professional_service",
                "professional_service__service",
                "address",
            )
            .prefetch_related("status_events", "declines")
            .order_by("-created_at")
        )

        if user.role == user.Role.ADMIN or user.is_staff:
            return queryset
        if user.role == user.Role.PROFESSIONAL:
            return queryset.filter(professional__user=user)
        return queryset.filter(customer=user)

    def _actor_is_customer(self, booking):
        return booking.customer_id == self.request.user.id

    def _actor_is_professional(self, booking):
        return booking.professional_id and booking.professional.user_id == self.request.user.id

    @staticmethod
    def _distance_meters(first_latitude, first_longitude, second_latitude, second_longitude):
        earth_radius = 6_371_000
        latitude_delta = radians(float(second_latitude) - float(first_latitude))
        longitude_delta = radians(float(second_longitude) - float(first_longitude))
        first_latitude = radians(float(first_latitude))
        second_latitude = radians(float(second_latitude))
        haversine = sin(latitude_delta / 2) ** 2 + cos(first_latitude) * cos(second_latitude) * sin(longitude_delta / 2) ** 2
        return earth_radius * 2 * asin(sqrt(haversine))

    @transaction.atomic
    def _transition(self, booking, next_status, note, allowed_statuses):
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        if booking.status not in allowed_statuses:
            return response.Response(
                {"detail": f"Booking cannot move from {booking.status} to {next_status}."},
                status=status.HTTP_409_CONFLICT,
            )
        booking.status = next_status
        timestamp_field = {
            Booking.Status.LEFT: "left_at",
            Booking.Status.REACHED: "reached_at",
            Booking.Status.STARTED: "started_at",
            Booking.Status.COMPLETED: "completed_at",
            Booking.Status.CONFIRMED_COMPLETE: "confirmed_complete_at",
        }.get(next_status)
        if timestamp_field:
            setattr(booking, timestamp_field, timezone.now())
        booking.save(update_fields=["status", timestamp_field, "updated_at"] if timestamp_field else ["status", "updated_at"])
        BookingStatusEvent.objects.create(booking=booking, status=next_status, note=note)
        recipients = [booking.customer]
        if booking.professional_id:
            recipients.append(booking.professional.user)
        for recipient in recipients:
            try:
                BookingNotification.objects.create(booking=booking, recipient=recipient, event=next_status, body=note)
            except Exception:
                pass
        return response.Response(self.get_serializer(booking).data)

    @decorators.action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        booking = self.get_object()
        if not self._actor_is_professional(booking):
            return response.Response({"detail": "Only the assigned professional can accept this booking."}, status=403)
        return self._transition(booking, Booking.Status.CONFIRMED, "Professional accepted booking.", [Booking.Status.PENDING_ACCEPT])

    @decorators.action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        booking = self.get_object()
        if not self._actor_is_professional(booking):
            return response.Response({"detail": "Only the assigned professional can decline this booking."}, status=403)
        reason = str(request.data.get("reason", "")).strip()[:255]
        if not reason:
            return response.Response({"reason": "A decline reason is required."}, status=400)
        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            if booking.status != Booking.Status.PENDING_ACCEPT:
                return response.Response({"detail": "Only pending bookings can be declined."}, status=409)
            BookingDecline.objects.create(booking=booking, professional=booking.professional, reason=reason)
        return self._transition(booking, Booking.Status.CANCELLED_PROFESSIONAL, reason, [Booking.Status.PENDING_ACCEPT])

    @decorators.action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if not self._actor_is_customer(booking) and not self._actor_is_professional(booking) and not request.user.is_staff:
            return response.Response({"detail": "You cannot cancel this booking."}, status=403)
        next_status = Booking.Status.CANCELLED_CUSTOMER if self._actor_is_customer(booking) else Booking.Status.CANCELLED_PROFESSIONAL
        cancellation_note = "Booking cancelled."
        if next_status == Booking.Status.CANCELLED_CUSTOMER and booking.booking_type == Booking.BookingType.SCHEDULED:
            cancellation_window = MarketplaceSettings.current().customer_cancellation_window_minutes
            if booking.scheduled_time and booking.scheduled_time - timezone.now() <= timedelta(minutes=cancellation_window):
                cancellation_note = "Booking cancelled inside the customer cancellation window; the booking amount is forfeited."
            else:
                cancellation_note = "Booking cancelled within the allowed window; the authorization is eligible for full refund."
        from payments.services import PaymentCaptureUnavailable, settle_cancellation_payment

        customer_late = next_status == Booking.Status.CANCELLED_CUSTOMER and booking.booking_type == Booking.BookingType.SCHEDULED and bool(booking.scheduled_time and booking.scheduled_time - timezone.now() <= timedelta(minutes=MarketplaceSettings.current().customer_cancellation_window_minutes))
        try:
            with transaction.atomic():
                settle_cancellation_payment(booking, customer_late=customer_late)
        except PaymentCaptureUnavailable as exc:
            return response.Response({"detail": str(exc.detail)}, status=503)
        except Exception as exc:
            return response.Response({"detail": str(exc)}, status=502)
        return self._transition(booking, next_status, cancellation_note, [Booking.Status.SEARCHING, Booking.Status.NO_MATCH, Booking.Status.PENDING_ACCEPT, Booking.Status.CONFIRMED, Booking.Status.AWAITING_REAFFIRMATION])

    @decorators.action(detail=True, methods=["post"])
    def reached(self, request, pk=None):
        booking = self.get_object()
        if not self._actor_is_professional(booking):
            return response.Response({"detail": "Only the assigned professional can confirm arrival."}, status=403)
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        if latitude is None or longitude is None or booking.address.latitude is None or booking.address.longitude is None:
            return response.Response({"detail": "Current GPS coordinates and a geocoded booking address are required."}, status=400)
        try:
            distance = self._distance_meters(latitude, longitude, booking.address.latitude, booking.address.longitude)
        except (TypeError, ValueError):
            return response.Response({"detail": "GPS coordinates must be valid numbers."}, status=400)
        if distance > settings.GPS_ARRIVAL_THRESHOLD_METERS:
            return response.Response({"detail": "You are outside the arrival verification radius.", "distance_meters": round(distance, 1)}, status=409)
        with transaction.atomic():
            booking.reached_latitude = latitude
            booking.reached_longitude = longitude
            booking.save(update_fields=["reached_latitude", "reached_longitude", "updated_at"])
        return self._transition(booking, Booking.Status.REACHED, "GPS arrival verified.", [Booking.Status.LEFT])

    @decorators.action(detail=True, methods=["post"])
    def left(self, request, pk=None):
        booking = self.get_object()
        if not self._actor_is_professional(booking):
            return response.Response({"detail": "Only the assigned professional can confirm departure."}, status=403)
        return self._transition(booking, Booking.Status.LEFT, "Professional left for the appointment.", [Booking.Status.CONFIRMED])

    @decorators.action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        booking = self.get_object()
        if not self._actor_is_professional(booking):
            return response.Response({"detail": "Only the assigned professional can start the booking."}, status=403)
        return self._transition(booking, Booking.Status.STARTED, "Work started.", [Booking.Status.REACHED])

    @decorators.action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        booking = self.get_object()
        if not self._actor_is_professional(booking):
            return response.Response({"detail": "Only the assigned professional can complete the booking."}, status=403)
        return self._transition(booking, Booking.Status.COMPLETED, "Professional marked work complete.", [Booking.Status.STARTED])

    @decorators.action(detail=True, methods=["post"], url_path="confirm-complete")
    def confirm_complete(self, request, pk=None):
        booking = self.get_object()
        if not self._actor_is_customer(booking):
            return response.Response({"detail": "Only the customer can confirm completion."}, status=403)
        if booking.status != Booking.Status.COMPLETED:
            return response.Response({"detail": "Only completed services can be confirmed."}, status=409)
        from payments.services import PaymentCaptureUnavailable, capture_booking_payment

        try:
            with transaction.atomic():
                capture_booking_payment(booking)
        except PaymentCaptureUnavailable as exc:
            return response.Response({"detail": str(exc.detail)}, status=503)
        except Exception as exc:
            return response.Response({"detail": str(exc)}, status=502)
        return self._transition(booking, Booking.Status.CONFIRMED_COMPLETE, "Customer confirmed completion.", [Booking.Status.COMPLETED])

    @decorators.action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        booking = self.get_object()
        if not self._actor_is_customer(booking):
            return response.Response({"detail": "Only the customer can reschedule this booking."}, status=403)
        if booking.booking_type != Booking.BookingType.SCHEDULED:
            return response.Response({"detail": "Only scheduled bookings can be rescheduled."}, status=409)
        new_time = parse_datetime(str(request.data.get("scheduled_time", "")))
        if new_time is None:
            return response.Response({"scheduled_time": "Provide a valid ISO-8601 datetime."}, status=400)
        slot_id = request.data.get("availability_slot")
        with transaction.atomic():
            locked = Booking.objects.select_for_update().select_related("professional_service").get(pk=booking.pk)
            if locked.status not in [Booking.Status.PENDING_ACCEPT, Booking.Status.CONFIRMED, Booking.Status.AWAITING_REAFFIRMATION]:
                return response.Response({"detail": "This booking cannot be rescheduled in its current state."}, status=409)
            slot_query = AvailabilitySlot.objects.select_for_update().filter(
                professional=locked.professional,
                is_booked=False,
                start_time__lte=new_time,
                end_time__gte=new_time + timedelta(minutes=locked.professional_service.duration_minutes),
            ).order_by("start_time")
            new_slot = slot_query.filter(pk=slot_id).first() if slot_id else slot_query.first()
            if new_slot is None:
                return response.Response({"detail": "No open availability slot fits that time."}, status=409)
            if locked.availability_slot_id:
                AvailabilitySlot.objects.filter(pk=locked.availability_slot_id).update(is_booked=False)
            new_slot.is_booked = True
            new_slot.save(update_fields=["is_booked"])
            locked.availability_slot = new_slot
            locked.scheduled_time = new_time
            locked.status = Booking.Status.PENDING_ACCEPT
            locked.save(update_fields=["availability_slot", "scheduled_time", "status", "updated_at"])
            BookingStatusEvent.objects.create(booking=locked, status=locked.status, note="Customer requested a new appointment time.")
        return response.Response(self.get_serializer(locked).data)


class AvailabilitySlotViewSet(viewsets.ModelViewSet):
    serializer_class = AvailabilitySlotSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    def get_queryset(self):
        queryset = AvailabilitySlot.objects.select_related("professional", "professional__user").order_by("start_time")
        if self.request.user.is_authenticated and self.request.user.role == self.request.user.Role.PROFESSIONAL:
            queryset = queryset.filter(professional__user=self.request.user)
        elif self.request.user.is_authenticated and (self.request.user.is_staff or self.request.user.role == self.request.user.Role.ADMIN):
            pass
        else:
            queryset = queryset.filter(is_booked=False)
        professional = self.request.query_params.get("professional")
        if professional:
            queryset = queryset.filter(professional_id=professional)
        return queryset

    def perform_create(self, serializer):
        if self.request.user.role != self.request.user.Role.PROFESSIONAL:
            raise PermissionDenied("Professional access required.")
        serializer.save(professional=self.request.user.professional_profile)

    def perform_update(self, serializer):
        if serializer.instance.is_booked:
            raise PermissionDenied("Booked availability cannot be changed.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.is_booked:
            raise PermissionDenied("Booked availability cannot be deleted.")
        instance.delete()


class BookingNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BookingNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BookingNotification.objects.filter(recipient=self.request.user)

    @decorators.action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
        return response.Response({"read": True})
