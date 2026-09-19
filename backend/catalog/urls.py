from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AdminCatalogView, CategoryViewSet, ProfessionalServiceManageViewSet, ProfessionalServiceViewSet, ServiceViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("services", ServiceViewSet, basename="service")
router.register("professional-services", ProfessionalServiceViewSet, basename="professional-service")
router.register("professional/manage-services", ProfessionalServiceManageViewSet, basename="professional-manage-service")

urlpatterns = [
    path("admin/catalog/", AdminCatalogView.as_view(), name="admin-catalog"),
    path("", include(router.urls)),
]
