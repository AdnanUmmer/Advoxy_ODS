from rest_framework import serializers

from .models import ProfessionalVerification


class ProfessionalVerificationSerializer(serializers.ModelSerializer):
    professional_name = serializers.CharField(source="professional.user.get_full_name", read_only=True)

    class Meta:
        model = ProfessionalVerification
        fields = [
            "id",
            "professional",
            "professional_name",
            "provider",
            "provider_reference_id",
            "status",
            "fee_paid",
            "identity_check_passed",
            "criminal_record_check_passed",
            "submitted_at",
            "decided_at",
            "expires_at",
        ]
        read_only_fields = fields


class VerificationSubmitSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(
        choices=ProfessionalVerification.Provider.choices,
        required=False,
    )
