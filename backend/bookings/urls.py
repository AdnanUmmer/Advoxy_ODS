from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .demo_views import DemoAvailabilityView, DemoBookingActionView, DemoProfessionalOnlineView, DemoScenarioView
from .views import AvailabilitySlotViewSet, BookingNotificationViewSet, BookingViewSet

router = DefaultRouter()
router.register("availability", AvailabilitySlotViewSet, basename="availability")
router.register("bookings", BookingViewSet, basename="booking")
router.register("notifications", BookingNotificationViewSet, basename="booking-notification")

urlpatterns = [
    path("demo/scenario/", DemoScenarioView.as_view(), name="demo-scenario"),
    path("demo/professionals/<int:professional_id>/online/", DemoProfessionalOnlineView.as_view(), name="demo-professional-online"),
    path("demo/professionals/<int:professional_id>/availability/", DemoAvailabilityView.as_view(), name="demo-professional-availability"),
    path("demo/bookings/<int:booking_id>/<slug:action>/", DemoBookingActionView.as_view(), name="demo-booking-action"),
    path("", include(router.urls)),
]
