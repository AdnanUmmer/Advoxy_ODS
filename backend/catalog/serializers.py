from rest_framework import serializers

from .models import Category, ProfessionalService, Service, SubCategory


class ServiceSerializer(serializers.ModelSerializer):
    subcategory_name = serializers.CharField(source="subcategory.name", read_only=True)
    subcategory_slug = serializers.CharField(source="subcategory.slug", read_only=True)
    audience = serializers.CharField(source="subcategory.audience", read_only=True)
    category_name = serializers.CharField(source="subcategory.category.name", read_only=True)
    category_slug = serializers.CharField(source="subcategory.category.slug", read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "name", "slug", "description", "duration_minutes", "default_price",
            "display_order", "is_active", "parent_service", "subcategory_name",
            "subcategory_slug", "audience", "category_name", "category_slug",
        ]


class SubCategorySerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = SubCategory
        fields = ["id", "name", "slug", "audience", "display_order", "services"]


class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "is_active", "subcategories"]


class ProfessionalServiceSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    category_name = serializers.CharField(
        source="service.subcategory.category.name",
        read_only=True,
    )
    service_slug = serializers.CharField(source="service.slug", read_only=True)
    subcategory_name = serializers.CharField(source="service.subcategory.name", read_only=True)
    subcategory_slug = serializers.CharField(source="service.subcategory.slug", read_only=True)
    category_slug = serializers.CharField(source="service.subcategory.category.slug", read_only=True)
    audience = serializers.CharField(source="service.subcategory.audience", read_only=True)
    professional_name = serializers.CharField(
        source="professional.user.get_full_name",
        read_only=True,
    )
    professional_rating = serializers.DecimalField(
        source="professional.average_rating",
        max_digits=3,
        decimal_places=2,
        read_only=True,
    )
    is_online = serializers.BooleanField(source="professional.is_online", read_only=True)
    is_available_now = serializers.SerializerMethodField()

    def get_is_available_now(self, obj):
        if not obj.professional.is_online:
            return False
        active_statuses = {
            "PENDING_ACCEPT",
            "CONFIRMED",
            "AWAITING_REAFFIRMATION",
            "LEFT",
            "REACHED",
            "STARTED",
            "COMPLETED",
        }
        return not obj.professional.bookings_as_professional.filter(status__in=active_statuses).exists()

    class Meta:
        model = ProfessionalService
        fields = [
            "id",
            "professional",
            "professional_name",
            "professional_rating",
            "is_online",
            "is_available_now",
            "service",
            "service_name",
            "service_slug",
            "category_name",
            "category_slug",
            "subcategory_name",
            "subcategory_slug",
            "audience",
            "price",
            "duration_minutes",
            "is_active",
        ]
        read_only_fields = ["id"]


class ProfessionalServiceManageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalService
        fields = ["id", "service", "price", "duration_minutes", "is_active"]
        read_only_fields = ["id"]

    def validate_service(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Only active catalog services can be offered.")
        return value

    def validate_duration_minutes(self, value):
        if value < 15 or value > 480:
            raise serializers.ValidationError("Duration must be between 15 minutes and 8 hours.")
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value
