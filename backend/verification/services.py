import hashlib
import hmac

import requests
from django.conf import settings
from rest_framework.exceptions import APIException

from .models import ProfessionalVerification


class VerificationProviderUnavailable(APIException):
    status_code = 503
    default_detail = "Identity verification provider is not configured."


def _professional_fields(professional):
    user = professional.user
    return {
        "name-first": user.first_name,
        "name-last": user.last_name,
        "birthdate": user.date_of_birth.isoformat(),
        "email": user.email,
        "reference-id": f"professional-{professional.pk}",
    }


def create_provider_reference(professional, provider):
    if provider == ProfessionalVerification.Provider.PERSONA:
        return _create_persona_inquiry(professional)
    if provider == ProfessionalVerification.Provider.CERTN:
        return _create_certn_applicant(professional)
    raise VerificationProviderUnavailable("Unsupported verification provider.")


def _create_persona_inquiry(professional):
    if not settings.PERSONA_API_KEY or not settings.PERSONA_TEMPLATE_ID or not settings.PERSONA_API_BASE_URL:
        raise VerificationProviderUnavailable("Persona API URL, API key, and template ID are required.")
    response = requests.post(
        f"{settings.PERSONA_API_BASE_URL.rstrip('/')}/inquiries",
        headers={
            "Authorization": f"Bearer {settings.PERSONA_API_KEY}",
            "Persona-Version": "2023-01-05",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "data": {
                "attributes": {
                    "inquiry-template-id": settings.PERSONA_TEMPLATE_ID,
                    "fields": _professional_fields(professional),
                }
            }
        },
        timeout=10,
    )
    if response.status_code >= 400:
        raise APIException("Persona could not create a verification inquiry.")
    return response.json()["data"]["id"]


def _create_certn_applicant(professional):
    if not settings.CERTN_API_KEY or not settings.CERTN_API_BASE_URL:
        raise VerificationProviderUnavailable("Certn API URL and API key are required.")
    user = professional.user
    response = requests.post(
        f"{settings.CERTN_API_BASE_URL.rstrip('/')}/applicants/",
        headers={
            "Authorization": f"Bearer {settings.CERTN_API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "email": user.email,
            "tag": f"professional-{professional.pk}",
            "information": {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "date_of_birth": user.date_of_birth.isoformat(),
            },
        },
        timeout=10,
    )
    if response.status_code >= 400:
        raise APIException("Certn could not create a verification applicant.")
    payload = response.json()
    return str(payload.get("id") or payload.get("applicant_id") or payload.get("uuid"))


def verify_signed_webhook(raw_body, header_value, secret):
    if not secret or not header_value:
        return False
    parts = {}
    for item in header_value.replace(" ", ",").split(","):
        if "=" in item:
            key, value = item.split("=", 1)
            parts.setdefault(key.strip().lower(), []).append(value.strip())
    timestamp = parts.get("t", [None])[0]
    signatures = parts.get("v1", [])
    if not timestamp or not signatures:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        timestamp.encode("utf-8") + b"." + raw_body,
        hashlib.sha256,
    ).hexdigest()
    return any(hmac.compare_digest(expected, signature) for signature in signatures)
