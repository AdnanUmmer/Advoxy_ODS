from django.urls import path

from .views import PersonaWebhookView, ProfessionalVerificationView, SubmitVerificationView

urlpatterns = [
    path("verification/me/", ProfessionalVerificationView.as_view(), name="verification-me"),
    path("verification/submit/", SubmitVerificationView.as_view(), name="verification-submit"),
    path("verification/webhook/persona/", PersonaWebhookView.as_view(), name="persona-webhook"),
]
