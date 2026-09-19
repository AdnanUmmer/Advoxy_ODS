from django.contrib import admin
from .models import PaymentAuthorization, Payout


@admin.register(PaymentAuthorization)
class PaymentAuthorizationAdmin(admin.ModelAdmin):
    list_display = ("booking", "amount", "status", "authorized_at", "captured_at")
    list_filter = ("status",)


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ("professional", "booking", "net_amount", "dispute_window_ends_at", "released_at")
    list_filter = ("released_at",)
