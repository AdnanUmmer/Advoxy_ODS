from decimal import Decimal

import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from bookings.models import Booking

from .models import PaymentAuthorization, Payout


class PaymentCaptureUnavailable(APIException):
    status_code = 503
    default_detail = "Payment capture is not configured for this environment."


def capture_booking_payment(booking):
    """Capture once and record the payout snapshot after confirmed completion."""
    authorization = PaymentAuthorization.objects.select_for_update().filter(booking=booking).first()
    if authorization is None or authorization.status == PaymentAuthorization.Status.CAPTURED:
        return authorization
    if authorization.status != PaymentAuthorization.Status.AUTHORIZED:
        raise APIException("This booking payment is not available for capture.")
    if authorization.provider != PaymentAuthorization.Provider.DEMO:
        if not settings.STRIPE_SECRET_KEY:
            raise PaymentCaptureUnavailable()
        if settings.DEBUG and settings.STRIPE_SECRET_KEY.startswith("sk_live_"):
            raise PaymentCaptureUnavailable("Development booking capture must use a Stripe test secret key.")

        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            intent = stripe.PaymentIntent.capture(authorization.stripe_payment_intent_id)
        except stripe.error.StripeError as exc:
            raise APIException("Stripe could not capture this payment.") from exc
        if intent.status != "succeeded":
            raise APIException("Stripe did not confirm payment capture.")

    with transaction.atomic():
        locked = PaymentAuthorization.objects.select_for_update().get(pk=authorization.pk)
        if locked.status == PaymentAuthorization.Status.CAPTURED:
            return locked
        locked.status = PaymentAuthorization.Status.CAPTURED
        locked.captured_at = timezone.now()
        locked.save(update_fields=["status", "captured_at"])
        Payout.objects.get_or_create(
            booking=booking,
            defaults={
                "professional": booking.professional,
                "gross_amount": booking.service_price + booking.travel_fee,
                "commission_amount": booking.platform_commission,
                "net_amount": booking.service_price + booking.travel_fee - booking.platform_commission,
                "dispute_window_ends_at": timezone.now(),
            },
        )
        from bookings.models import BookingNotification

        BookingNotification.objects.get_or_create(
            booking=booking,
            recipient=booking.customer,
            event="PAYMENT_CAPTURED",
            defaults={"body": "Your payment was captured after completion."},
        )
        if booking.professional_id:
            BookingNotification.objects.get_or_create(
                booking=booking,
                recipient=booking.professional.user,
                event="PAYMENT_CAPTURED",
                defaults={"body": "Payment was captured and your earnings were recorded."},
            )
    return locked


def settle_cancellation_payment(booking, *, customer_late=False):
    """Cancel an authorization, or refund a capture, without trusting client state."""
    authorization = PaymentAuthorization.objects.select_for_update().filter(booking=booking).first()
    if authorization is None:
        return None
    if not settings.STRIPE_SECRET_KEY:
        raise PaymentCaptureUnavailable()
    if settings.DEBUG and settings.STRIPE_SECRET_KEY.startswith("sk_live_"):
        raise PaymentCaptureUnavailable("Development booking settlement must use a Stripe test secret key.")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        if customer_late and authorization.status == PaymentAuthorization.Status.AUTHORIZED:
            stripe.PaymentIntent.capture(authorization.stripe_payment_intent_id)
            authorization.status = PaymentAuthorization.Status.CAPTURED
            authorization.captured_at = timezone.now()
        elif authorization.status == PaymentAuthorization.Status.CAPTURED:
            stripe.Refund.create(payment_intent=authorization.stripe_payment_intent_id, idempotency_key=f"booking-refund-{booking.id}")
            authorization.status = PaymentAuthorization.Status.REFUNDED
            authorization.refunded_at = timezone.now()
        elif authorization.status in {PaymentAuthorization.Status.PENDING, PaymentAuthorization.Status.AUTHORIZED}:
            stripe.PaymentIntent.cancel(authorization.stripe_payment_intent_id, idempotency_key=f"booking-cancel-{booking.id}")
            authorization.status = PaymentAuthorization.Status.CANCELLED
        else:
            return authorization
    except stripe.error.StripeError as exc:
        raise APIException("Stripe could not settle the cancelled booking payment.") from exc
    authorization.save(update_fields=["status", "captured_at", "refunded_at"])
    return authorization


def create_professional_transfer(payout):
    """Request a Connect transfer only for an eligible, configured payout."""
    professional = payout.professional
    if payout.status == Payout.Status.PAID:
        return payout
    if not settings.STRIPE_SECRET_KEY or not professional.stripe_connect_account_id or not professional.stripe_connect_payouts_enabled:
        raise PaymentCaptureUnavailable("Stripe Connect payout is not configured for this professional.")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        transfer = stripe.Transfer.create(
            amount=int(payout.net_amount * 100),
            currency="cad",
            destination=professional.stripe_connect_account_id,
            transfer_group=f"booking-{payout.booking_id}",
            idempotency_key=f"booking-transfer-{payout.booking_id}",
        )
    except stripe.error.StripeError as exc:
        payout.status = Payout.Status.FAILED
        payout.provider_error = "Stripe Connect transfer failed."
        payout.save(update_fields=["status", "provider_error"])
        raise APIException("Stripe Connect could not create the professional transfer.") from exc
    payout.stripe_transfer_id = transfer.id
    payout.status = Payout.Status.PROCESSING
    payout.provider_error = ""
    payout.save(update_fields=["stripe_transfer_id", "status", "provider_error"])
    return payout
