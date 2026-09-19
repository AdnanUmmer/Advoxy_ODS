from decimal import Decimal

import stripe
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking

from .models import PaymentAuthorization, Payout, StripeEvent


class PaymentIntentView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		booking_id = request.data.get("booking")
		if not settings.STRIPE_SECRET_KEY:
			return Response({"detail": "Stripe is not configured for this environment."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
		if settings.DEBUG and settings.STRIPE_SECRET_KEY.startswith("sk_live_"):
			return Response({"detail": "Development bookings must use a Stripe test secret key."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
		try:
			with transaction.atomic():
				booking = Booking.objects.select_for_update().select_related("customer").get(
					pk=booking_id,
					customer=request.user,
				)
				if booking.status in {Booking.Status.CANCELLED_CUSTOMER, Booking.Status.CANCELLED_PROFESSIONAL, Booking.Status.NO_MATCH}:
					return Response({"detail": "Cancelled bookings cannot be paid."}, status=status.HTTP_409_CONFLICT)
				if PaymentAuthorization.objects.filter(booking=booking).exists():
					return Response({"detail": "This booking already has a payment authorization."}, status=status.HTTP_409_CONFLICT)
				amount = Decimal(booking.total_amount)
				stripe.api_key = settings.STRIPE_SECRET_KEY
				try:
					intent = stripe.PaymentIntent.create(
						amount=int(amount * 100),
						currency="cad",
						capture_method="manual",
						payment_method_types=["card"],
						metadata={"booking_id": str(booking.id)},
						idempotency_key=f"booking-payment-{booking.id}",
					)
				except stripe.error.StripeError as exc:
					return Response({"detail": "Stripe could not authorize this payment."}, status=status.HTTP_502_BAD_GATEWAY)
				if intent.status not in {"requires_capture", "requires_action", "requires_payment_method"}:
					return Response({"detail": "Stripe returned an unsupported payment state."}, status=status.HTTP_502_BAD_GATEWAY)
				PaymentAuthorization.objects.create(
					booking=booking,
					stripe_payment_intent_id=intent.id,
					amount=amount,
					status=PaymentAuthorization.Status.AUTHORIZED if intent.status == "requires_capture" else PaymentAuthorization.Status.PENDING,
				)
			return Response({"payment_intent_id": intent.id, "client_secret": intent.client_secret, "status": intent.status}, status=status.HTTP_201_CREATED)
		except Booking.DoesNotExist:
			return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
		except IntegrityError:
			return Response({"detail": "This booking already has a payment authorization."}, status=status.HTTP_409_CONFLICT)


class PaymentConfirmView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		payment_intent_id = str(request.data.get("payment_intent_id", "")).strip()
		if not payment_intent_id:
			return Response({"detail": "A Stripe payment intent is required."}, status=status.HTTP_400_BAD_REQUEST)
		if not settings.STRIPE_SECRET_KEY:
			return Response({"detail": "Stripe is not configured for this environment."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
		try:
			stripe.api_key = settings.STRIPE_SECRET_KEY
			intent = stripe.PaymentIntent.retrieve(payment_intent_id)
		except stripe.error.StripeError as exc:
			return Response({"detail": "Stripe could not verify this payment."}, status=status.HTTP_502_BAD_GATEWAY)
		try:
			authorization = PaymentAuthorization.objects.select_related("booking").get(
				stripe_payment_intent_id=payment_intent_id,
				booking__customer=request.user,
			)
		except PaymentAuthorization.DoesNotExist:
			return Response({"detail": "Payment authorization not found."}, status=status.HTTP_404_NOT_FOUND)
		if intent.status not in {"requires_capture", "succeeded"}:
			return Response({"detail": f"Stripe has not confirmed this payment yet ({intent.status})."}, status=status.HTTP_409_CONFLICT)
		if intent.status == "succeeded":
			authorization.status = PaymentAuthorization.Status.CAPTURED
			authorization.captured_at = authorization.captured_at or timezone.now()
		else:
			authorization.status = PaymentAuthorization.Status.AUTHORIZED
		authorization.save(update_fields=["status", "captured_at"])
		return Response({"status": authorization.status, "payment_intent_id": payment_intent_id})


class StripeWebhookView(APIView):
	authentication_classes = []
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		if not settings.STRIPE_WEBHOOK_SECRET:
			return Response({"detail": "Stripe webhook signing is not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
		signature = request.headers.get("Stripe-Signature")
		try:
			event = stripe.Webhook.construct_event(request.body, signature, settings.STRIPE_WEBHOOK_SECRET)
		except (ValueError, stripe.error.SignatureVerificationError):
			return Response({"detail": "Invalid Stripe webhook signature."}, status=status.HTTP_400_BAD_REQUEST)

		event_type = event["type"]
		event_id = event["id"]
		intent = event["data"]["object"]
		if StripeEvent.objects.filter(event_id=event_id).exists():
			return Response({"received": True, "duplicate": True})
		if event_type.startswith("transfer."):
			with transaction.atomic():
				StripeEvent.objects.create(event_id=event_id, event_type=event_type)
				payout = Payout.objects.select_for_update().filter(stripe_transfer_id=intent["id"]).first()
				if payout:
					payout.status = {
						"transfer.paid": Payout.Status.PAID,
						"transfer.created": Payout.Status.PROCESSING,
						"transfer.failed": Payout.Status.FAILED,
						"transfer.reversed": Payout.Status.REVERSED,
					}[event_type]
					if event_type in {"transfer.failed", "transfer.reversed"}:
						payout.provider_error = "Stripe reported a transfer failure or reversal."
					payout.save(update_fields=["status", "provider_error"])
			return Response({"received": True})
		authorization = PaymentAuthorization.objects.filter(stripe_payment_intent_id=intent["id"]).first()
		if authorization is None:
			StripeEvent.objects.create(event_id=event_id, event_type=event_type)
			return Response({"received": True})
		with transaction.atomic():
			StripeEvent.objects.create(event_id=event_id, event_type=event_type)
			locked = PaymentAuthorization.objects.select_for_update().get(pk=authorization.pk)
			if event_type in {"payment_intent.amount_capturable_updated", "payment_intent.requires_capture"}:
				locked.status = PaymentAuthorization.Status.AUTHORIZED
				locked.save(update_fields=["status"])
			elif event_type == "payment_intent.succeeded":
				locked.status = PaymentAuthorization.Status.CAPTURED
				locked.captured_at = locked.captured_at or timezone.now()
				locked.save(update_fields=["status", "captured_at"])
				booking = locked.booking
				if booking.professional_id:
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
			elif event_type == "payment_intent.payment_failed":
				locked.status = PaymentAuthorization.Status.FAILED
				locked.save(update_fields=["status"])
			elif event_type == "payment_intent.canceled":
				locked.status = PaymentAuthorization.Status.CANCELLED
				locked.save(update_fields=["status"])
			elif event_type in {"transfer.paid", "transfer.created"}:
				payout = Payout.objects.filter(stripe_transfer_id=intent["id"]).first()
				if payout:
					payout.status = Payout.Status.PAID if event_type == "transfer.paid" else Payout.Status.PROCESSING
					payout.save(update_fields=["status"])
			elif event_type in {"transfer.failed", "transfer.reversed"}:
				payout = Payout.objects.filter(stripe_transfer_id=intent["id"]).first()
				if payout:
					payout.status = Payout.Status.FAILED if event_type == "transfer.failed" else Payout.Status.REVERSED
					payout.provider_error = "Stripe reported a transfer failure or reversal."
					payout.save(update_fields=["status", "provider_error"])
		return Response({"received": True})
