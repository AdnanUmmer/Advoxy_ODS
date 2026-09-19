from django.urls import path

from .views import PaymentConfirmView, PaymentIntentView, StripeWebhookView

urlpatterns = [
    path("payments/intent/", PaymentIntentView.as_view(), name="payment-intent"),
    path("payments/confirm/", PaymentConfirmView.as_view(), name="payment-confirm"),
    path("payments/webhook/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
]