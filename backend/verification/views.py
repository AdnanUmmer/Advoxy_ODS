import json

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import ProfessionalProfile, User

from .models import ProfessionalVerification
from .serializers import ProfessionalVerificationSerializer, VerificationSubmitSerializer
from .services import create_provider_reference, verify_signed_webhook


class ProfessionalVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != User.Role.PROFESSIONAL:
            return Response({"detail": "Professional access required."}, status=403)
        profile, _ = ProfessionalProfile.objects.get_or_create(user=request.user)
        verification = ProfessionalVerification.objects.filter(professional=profile).first()
        if verification is None:
            return Response({"detail": "No verification submission exists yet."}, status=404)
        return Response(ProfessionalVerificationSerializer(verification).data)


class SubmitVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != User.Role.PROFESSIONAL:
            return Response({"detail": "Professional access required."}, status=403)
        serializer = VerificationSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile, _ = ProfessionalProfile.objects.get_or_create(user=request.user)
        existing = ProfessionalVerification.objects.filter(
            professional=profile,
            status__in=[
                ProfessionalVerification.Status.PENDING,
                ProfessionalVerification.Status.APPROVED,
            ],
        ).first()
        if existing:
            return Response(ProfessionalVerificationSerializer(existing).data)

        provider_name = serializer.validated_data.get("provider") or settings.IDENTITY_VERIFICATION_PROVIDER.upper()
        provider = ProfessionalVerification.Provider(provider_name)
        reference_id = create_provider_reference(profile, provider)
        verification = ProfessionalVerification.objects.create(
            professional=profile,
            provider=provider,
            provider_reference_id=reference_id,
            status=ProfessionalVerification.Status.PENDING,
            fee_paid=True,
        )
        return Response(ProfessionalVerificationSerializer(verification).data, status=201)


class PersonaWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if not verify_signed_webhook(
            request.body,
            request.headers.get("Persona-Signature", ""),
            settings.PERSONA_WEBHOOK_SECRET,
        ):
            return Response({"detail": "Invalid Persona webhook signature."}, status=401)
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except ValueError:
            return Response({"detail": "Invalid JSON payload."}, status=400)

        event = payload.get("data", {})
        attributes = event.get("attributes", {})
        event_name = attributes.get("name", "")
        inquiry = attributes.get("payload", {}).get("data", {})
        reference_id = inquiry.get("id")
        if not reference_id:
            return Response({"received": True})

        verification = ProfessionalVerification.objects.select_related("professional").filter(
            provider=ProfessionalVerification.Provider.PERSONA,
            provider_reference_id=reference_id,
        ).first()
        if verification is None:
            return Response({"received": True})

        status_map = {
            "inquiry.approved": ProfessionalVerification.Status.APPROVED,
            "inquiry.declined": ProfessionalVerification.Status.REJECTED,
            "inquiry.expired": ProfessionalVerification.Status.EXPIRED,
            "inquiry.completed": ProfessionalVerification.Status.PENDING,
        }
        next_status = status_map.get(event_name)
        if not next_status:
            return Response({"received": True})

        decision_statuses = {
            ProfessionalVerification.Status.APPROVED,
            ProfessionalVerification.Status.REJECTED,
            ProfessionalVerification.Status.EXPIRED,
        }
        with transaction.atomic():
            verification = ProfessionalVerification.objects.select_for_update().get(pk=verification.pk)
            verification.status = next_status
            if next_status in decision_statuses:
                verification.decided_at = timezone.now()
                verification.identity_check_passed = next_status == ProfessionalVerification.Status.APPROVED
                verification.criminal_record_check_passed = next_status == ProfessionalVerification.Status.APPROVED
            verification.save(update_fields=[
                "status",
                "decided_at",
                "identity_check_passed",
                "criminal_record_check_passed",
            ])
            verification.professional.is_active = next_status == ProfessionalVerification.Status.APPROVED
            verification.professional.save(update_fields=["is_active"])
        return Response({"received": True})
