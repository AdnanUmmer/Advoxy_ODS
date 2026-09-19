from django.contrib import admin
from .models import ProfessionalVerification


@admin.register(ProfessionalVerification)
class ProfessionalVerificationAdmin(admin.ModelAdmin):
    list_display = ("professional", "provider", "status", "fee_paid", "submitted_at", "decided_at", "is_demo")
    list_filter = ("provider", "status", "fee_paid", "is_demo")
    readonly_fields = ("provider_reference_id", "submitted_at")
    actions = ["approve_selected", "reject_selected"]

    @admin.action(description="Approve selected verifications")
    def approve_selected(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status="APPROVED", decided_at=timezone.now(), decided_by=request.user)
        for v in queryset:
            v.professional.is_active = True
            v.professional.save(update_fields=["is_active"])
        self.message_user(request, f"{updated} verification(s) approved.")

    @admin.action(description="Reject selected verifications")
    def reject_selected(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status="REJECTED", decided_at=timezone.now(), decided_by=request.user)
        self.message_user(request, f"{updated} verification(s) rejected.")
