from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from .models import User, Address, ProfessionalProfile



class RegisterSerializer(serializers.ModelSerializer):
    """
    Signup for both CUSTOMER and PROFESSIONAL roles (Section 2 — role
    is chosen at signup, not assigned later). Enforces the 18+ minimum
    from Section 11 at the API boundary, not just as a UI hint.
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "password",
            "first_name", "last_name", "phone_number",
            "date_of_birth", "role",
        ]
        extra_kwargs = {
            "role": {"required": True},
        }

    def validate_role(self, value):
        if value == User.Role.ADMIN:
            raise serializers.ValidationError(
                "Admin accounts cannot be created through public signup."
            )
        return value

    def validate_date_of_birth(self, value):
        today = timezone.now().date()
        eighteenth_birthday = value.replace(year=value.year + 18)
        if today < eighteenth_birthday:
            raise serializers.ValidationError("You must be 18 or older to use Advoxy.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        # A PROFESSIONAL signup gets an empty profile immediately so
        # every downstream FK (verification, services offered) has
        # somewhere to attach — it stays is_active=False until
        # verification is approved (see verification app).
        if user.role == User.Role.PROFESSIONAL:
            ProfessionalProfile.objects.create(user=user)

        return user


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "label", "full_address", "latitude", "longitude", "is_default"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class UserSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "phone_number", "phone_verified", "role", "addresses",
        ]
        read_only_fields = ["id", "role", "phone_verified"]


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self, **kwargs):
        user = User.objects.filter(email__iexact=self.validated_data["email"], is_active=True).first()
        if user:
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password"
            send_mail(
                "Reset your Advoxy password",
                f"Use this reset link: {reset_url}?uid={user.pk}&token={token}",
                None,
                [user.email],
                fail_silently=False,
            )


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.IntegerField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate(self, attrs):
        try:
            user = User.objects.get(pk=attrs["uid"], is_active=True)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("This reset link is invalid or expired.") from exc
        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError("This reset link is invalid or expired.")
        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class ProfessionalProfileSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    display_name = serializers.CharField(source="user.get_full_name", read_only=True)
    area = serializers.CharField(source="base_address.label", read_only=True)
    services = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = ProfessionalProfile
        fields = [
            "id", "user", "display_name", "area", "bio", "years_experience", "service_radius_km",
            "free_travel_radius_km", "per_km_travel_fee", "is_online",
            "is_active", "base_address", "average_rating", "review_count",
            "service_cities",
            "services",
            "distance_km",
        ]
        # is_active is verification-gated, not self-settable — see
        # verification.admin.approve_selected, which is the only place
        # that's allowed to flip this to True right now.
        read_only_fields = ["id", "is_active", "average_rating", "review_count"]

    def get_services(self, obj):
        return [
            {
                "id": service.id,
                "service_catalog_id": service.service_id,
                "name": service.service.name,
                "slug": service.service.slug,
                "category": service.service.subcategory.category.name,
                "category_slug": service.service.subcategory.category.slug,
                "subcategory": service.service.subcategory.name,
                "subcategory_slug": service.service.subcategory.slug,
                "audience": service.service.subcategory.audience,
                "price": str(service.price),
                "duration_minutes": service.duration_minutes,
            }
            for service in obj.services_offered.filter(is_active=True).select_related(
                "service",
                "service__subcategory",
                "service__subcategory__category",
            )
        ]

    def get_user(self, obj):
        return {
            "id": obj.user_id,
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
            "role": obj.user.role,
        }

    def get_distance_km(self, obj):
        distance = getattr(obj, "_search_distance_km", None)
        return round(distance, 2) if distance is not None else None
