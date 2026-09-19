from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AddressGeocodeView, AdminDashboardView, AddressViewSet, GoogleLoginView, LoginView, LogoutView, MarketplaceSettingsView, MeView, PasswordResetConfirmView, PasswordResetRequestView, PlaceDetailsView, PlacesAutocompleteView, ProfessionalDashboardView, ProfessionalProfileManageView, ProfessionalProfileViewSet, ProfessionalStatusView, RegisterView, ReverseGeocodeView
from .favorites import FavoriteProfessionalView

router = DefaultRouter()
router.register("addresses", AddressViewSet, basename="address")
router.register("professionals", ProfessionalProfileViewSet, basename="professional")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/google/", GoogleLoginView.as_view(), name="google-login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("location/reverse/", ReverseGeocodeView.as_view(), name="location-reverse"),
    path("location/autocomplete/", PlacesAutocompleteView.as_view(), name="location-autocomplete"),
    path("location/geocode/", AddressGeocodeView.as_view(), name="location-geocode"),
    path("location/details/", PlaceDetailsView.as_view(), name="location-details"),
    path("favorites/", FavoriteProfessionalView.as_view(), name="favorites"),
    path("favorites/<int:professional_id>/", FavoriteProfessionalView.as_view(), name="favorite-professional"),
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("admin/settings/", MarketplaceSettingsView.as_view(), name="marketplace-settings"),
    path("professional/dashboard/", ProfessionalDashboardView.as_view(), name="professional-dashboard"),
    path("professional/status/", ProfessionalStatusView.as_view(), name="professional-status"),
    path("professional/profile/", ProfessionalProfileManageView.as_view(), name="professional-profile"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
