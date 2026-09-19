from django.contrib import admin
from .models import (
    Category,
    MarketplaceSettings,
    MarketplaceSettingsAudit,
    ProfessionalService,
    Service,
    SubCategory,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "audience", "display_order", "is_demo")
    list_filter = ("category", "audience", "is_demo")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "subcategory", "duration_minutes", "default_price", "is_active", "is_demo")
    list_filter = ("subcategory__category", "is_active", "is_demo")
    search_fields = ("name", "slug")


@admin.register(ProfessionalService)
class ProfessionalServiceAdmin(admin.ModelAdmin):
    list_display = ("professional", "service", "price", "duration_minutes", "is_active")
    list_filter = ("is_active",)


@admin.register(MarketplaceSettings)
class MarketplaceSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Search & distance", {"fields": ("instant_initial_radius_km", "instant_max_radius_km", "scheduled_search_radius_km", "radius_expansion_step_km", "professional_service_radius_km", "maximum_travel_distance_km")}),
        ("Pricing & travel", {"fields": ("included_travel_distance_km", "travel_fee_per_km", "maximum_travel_fee", "minimum_booking_price", "commission_percent", "fixed_platform_fee", "minimum_platform_fee", "maximum_platform_fee")}),
        ("Booking", {"fields": ("customer_cancellation_window_minutes", "professional_acceptance_window_minutes", "scheduled_minimum_notice_minutes", "maximum_advance_booking_days", "instant_booking_timeout_minutes", "rematching_timeout_minutes", "reminder_minutes_before_booking")}),
        ("Feature flags", {"fields": ("instant_booking_enabled", "scheduled_booking_enabled", "multiple_service_booking_enabled", "rematching_enabled", "travel_fees_enabled")}),
        ("Ranking", {"fields": ("availability_weight", "distance_weight", "rating_weight", "review_count_weight", "experience_weight", "reliability_weight")}),
        ("Tax", {"fields": ("tax_enabled", "tax_name", "tax_percent")}),
    )

    def has_add_permission(self, request):
        return not MarketplaceSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MarketplaceSettingsAudit)
class MarketplaceSettingsAuditAdmin(admin.ModelAdmin):
    list_display = ("settings", "admin", "created_at", "reason")
    readonly_fields = ("settings", "admin", "changes", "reason", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
