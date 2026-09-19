from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("booking", "reviewer", "reviewee", "rating", "flagged_for_admin", "created_at")
    list_filter = ("flagged_for_admin", "rating")
    readonly_fields = ("flagged_for_admin",)
