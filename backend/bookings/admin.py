from django.contrib import admin
from .models import Booking, BookingDecline, BookingStatusEvent, AvailabilitySlot


class BookingStatusEventInline(admin.TabularInline):
    model = BookingStatusEvent
    extra = 0
    readonly_fields = ("status", "occurred_at", "note")


class BookingDeclineInline(admin.TabularInline):
    model = BookingDecline
    extra = 0
    readonly_fields = ("professional", "reason", "declined_at")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "professional", "booking_type", "status", "total_amount", "created_at", "is_demo")
    list_filter = ("booking_type", "status", "is_demo")
    search_fields = ("customer__username", "professional__user__username")
    inlines = [BookingStatusEventInline, BookingDeclineInline]


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ("professional", "start_time", "end_time", "is_booked", "is_demo")
    list_filter = ("is_booked", "is_demo")
