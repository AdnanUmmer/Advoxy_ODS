from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Address, ProfessionalProfile, User
from catalog.models import ProfessionalService, Service
from payments.services import PaymentCaptureUnavailable, capture_booking_payment
from reviews.models import Review

from .models import AvailabilitySlot, Booking, BookingDecline, BookingNotification, BookingStatusEvent
from .serializers import BookingSerializer


class DemoToolsPermission(permissions.BasePermission):
    message = "Demo booking tools are available only to admins in development/test mode."

    def has_permission(self, request, view):
        return bool(
            settings.DEMO_BOOKING_TOOLS_ENABLED
            and request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.role == User.Role.ADMIN)
        )


def _notify(booking, event, body):
    recipients = [booking.customer]
    if booking.professional_id:
        recipients.append(booking.professional.user)
    for recipient in recipients:
        BookingNotification.objects.create(
            booking=booking,
            recipient=recipient,
            event=event,
            body=body,
            is_demo=True,
        )


def _set_status(booking, next_status, note):
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
    booking.is_demo = True
    booking.save(update_fields=["status", "is_demo", "updated_at"] + ([timestamp_field] if timestamp_field else []))
    BookingStatusEvent.objects.create(booking=booking, status=next_status, note=note)
    _notify(booking, next_status, note)
    return booking


class DemoScenarioView(APIView):
    permission_classes = [DemoToolsPermission]

    def get(self, request):
        service = Service.objects.filter(slug="mens-haircut", is_active=True).first()
        professional_service = (
            ProfessionalService.objects.filter(service=service, professional__is_active=True, is_active=True)
            .select_related("professional", "professional__user", "service")
            .first()
            if service
            else None
        )
        customer = User.objects.filter(email="demo_customer_01@demo.advoxy.test").first()
        professional = professional_service.professional if professional_service else None
        address = Address.objects.filter(user=customer, is_default=True).first() if customer else None
        slot = (
            AvailabilitySlot.objects.filter(professional=professional, is_booked=False, start_time__gt=timezone.now())
            .order_by("start_time")
            .first()
            if professional
            else None
        )
        return Response({
            "enabled": True,
            "stripe_mode": "test" if settings.STRIPE_SECRET_KEY.startswith("sk_test_") else "not_configured",
            "demo_password": "DemoOnly-Advoxy-2026!",
            "customer_email": getattr(customer, "email", ""),
            "professional_email": getattr(getattr(professional, "user", None), "email", ""),
            "admin_email": "demo_admin@demo.advoxy.test",
            "location": getattr(address, "full_address", "Demo Home, Calgary, AB"),
            "service": "Hair / Men / Men's Haircut",
            "service_id": getattr(service, "id", None),
            "professional_service_id": getattr(professional_service, "id", None),
            "professional_id": getattr(professional, "id", None),
            "address_id": getattr(address, "id", None),
            "availability_slot_id": getattr(slot, "id", None),
            "scheduled_time": slot.start_time.isoformat() if slot else "",
            "search_url": f"/search?service={getattr(service, 'id', '')}&service_name=Men%27s+Haircut&location=Calgary&booking_type=SCHEDULED",
            "book_url": f"/book?professionalService={getattr(professional_service, 'id', '')}&service={getattr(service, 'id', '')}&service_name=Men%27s+Haircut&location=Calgary&booking_type=SCHEDULED",
        })


class DemoProfessionalOnlineView(APIView):
    permission_classes = [DemoToolsPermission]

    def post(self, request, professional_id):
        profile = ProfessionalProfile.objects.get(pk=professional_id)
        profile.is_online = bool(request.data.get("is_online", True))
        profile.is_demo = True
        profile.save(update_fields=["is_online", "is_demo"])
        return Response({"professional": profile.id, "is_online": profile.is_online})


class DemoAvailabilityView(APIView):
    permission_classes = [DemoToolsPermission]

    def post(self, request, professional_id):
        profile = ProfessionalProfile.objects.get(pk=professional_id)
        start_time = timezone.now() + timedelta(hours=int(request.data.get("hours_from_now", 24)))
        start_time = start_time.replace(minute=0, second=0, microsecond=0)
        slot = AvailabilitySlot.objects.create(
            professional=profile,
            start_time=start_time,
            end_time=start_time + timedelta(minutes=int(request.data.get("duration_minutes", 180))),
            is_demo=True,
        )
        return Response({"availability_slot_id": slot.id, "start_time": slot.start_time, "end_time": slot.end_time}, status=status.HTTP_201_CREATED)


class DemoBookingActionView(APIView):
    permission_classes = [DemoToolsPermission]

    def post(self, request, booking_id, action):
        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .select_related("customer", "professional", "professional__user", "professional_service", "professional_service__service", "address")
                .get(pk=booking_id)
            )

            if action == "match":
                return self._match(booking)
            if action == "accept":
                return self._status(booking, Booking.Status.CONFIRMED, "Demo: professional accepted the booking.")
            if action == "decline":
                return self._decline(booking, str(request.data.get("reason", "")).strip())
            if action == "left":
                return self._status(booking, Booking.Status.LEFT, "Demo: professional left for the appointment.")
            if action == "arrival-eligibility":
                return Response({
                    "eligible": bool(booking.address.latitude and booking.address.longitude),
                    "latitude": booking.address.latitude,
                    "longitude": booking.address.longitude,
                    "threshold_meters": settings.GPS_ARRIVAL_THRESHOLD_METERS,
                })
            if action == "reached":
                booking.reached_latitude = booking.address.latitude
                booking.reached_longitude = booking.address.longitude
                booking.save(update_fields=["reached_latitude", "reached_longitude", "updated_at"])
                return self._status(booking, Booking.Status.REACHED, "Demo: GPS arrival verified.")
            if action == "started":
                return self._status(booking, Booking.Status.STARTED, "Demo: work started.")
            if action == "completed":
                return self._status(booking, Booking.Status.COMPLETED, "Demo: professional marked work complete.")
            if action == "confirm-complete":
                try:
                    capture_booking_payment(booking)
                except PaymentCaptureUnavailable as exc:
                    return Response({"detail": str(exc.detail)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                return self._status(booking, Booking.Status.CONFIRMED_COMPLETE, "Demo: customer confirmed completion and Stripe test capture ran.")
            if action == "review":
                return self._review(booking, int(request.data.get("rating", 5)), str(request.data.get("comment", "Great demo service.")))

        return Response({"detail": "Unknown demo booking action."}, status=status.HTTP_404_NOT_FOUND)

    def _serialize(self, booking):
        return Response(BookingSerializer(booking, context={"request": self.request}).data)

    def _status(self, booking, next_status, note):
        _set_status(booking, next_status, note)
        return self._serialize(booking)

    def _match(self, booking):
        service = booking.professional_service.service
        next_service = (
            ProfessionalService.objects.select_related("professional", "professional__user")
            .filter(service=service, professional__is_active=True, professional__is_online=True, is_active=True)
            .exclude(professional__bookings_as_professional__status__in=[
                Booking.Status.PENDING_ACCEPT,
                Booking.Status.CONFIRMED,
                Booking.Status.LEFT,
                Booking.Status.REACHED,
                Booking.Status.STARTED,
                Booking.Status.COMPLETED,
            ])
            .first()
        )
        if next_service is None:
            _set_status(booking, Booking.Status.NO_MATCH, "Demo: no matching professional is available.")
            return self._serialize(booking)
        booking.professional_service = next_service
        booking.professional = next_service.professional
        booking.save(update_fields=["professional_service", "professional", "updated_at"])
        _set_status(booking, Booking.Status.PENDING_ACCEPT, "Demo: matching professional assigned.")
        return self._serialize(booking)

    def _decline(self, booking, reason):
        if not reason:
            return Response({"reason": "A decline reason is required."}, status=status.HTTP_400_BAD_REQUEST)
        if booking.professional_id:
            BookingDecline.objects.create(booking=booking, professional=booking.professional, reason=reason)
        response = self._match(booking)
        if response.data["status"] == Booking.Status.NO_MATCH:
            _set_status(booking, Booking.Status.CANCELLED_PROFESSIONAL, reason)
            return self._serialize(booking)
        return response

    def _review(self, booking, rating, comment):
        if booking.status != Booking.Status.CONFIRMED_COMPLETE:
            return Response({"detail": "Complete and confirm the booking before creating a review."}, status=status.HTTP_409_CONFLICT)
        review, created = Review.objects.get_or_create(
            booking=booking,
            reviewer=booking.customer,
            defaults={
                "reviewee": booking.professional.user,
                "rating": rating,
                "comment": comment,
                "is_demo": True,
            },
        )
        return Response({"review_id": review.id, "created": created, "rating": review.rating})
