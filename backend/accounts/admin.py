from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, Address, ProfessionalProfile


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "phone_number", "phone_verified", "is_active", "is_demo")
    list_filter = ("role", "phone_verified", "is_active", "is_demo")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Advoxy", {"fields": ("role", "phone_number", "date_of_birth", "phone_verified")}),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "full_address", "is_default")
    search_fields = ("full_address", "user__username")


@admin.register(ProfessionalProfile)
class ProfessionalProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_active", "is_online", "average_rating", "review_count", "service_radius_km", "is_demo")
    list_filter = ("is_active", "is_online", "is_demo")
