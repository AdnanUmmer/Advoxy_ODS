from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

from .models import Category, MarketplaceSettings, ProfessionalService, Service
from .serializers import (
    CategorySerializer,
    ProfessionalServiceSerializer,
    ProfessionalServiceManageSerializer,
    ServiceSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Category.objects.filter(is_active=True)
            .prefetch_related("subcategories__services")
            .order_by("name")
        )


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Service.objects.filter(is_active=True).select_related(
            "subcategory",
            "subcategory__category",
        )
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(subcategory__category__slug=category)
        audience = self.request.query_params.get("audience")
        if audience:
            queryset = queryset.filter(subcategory__audience=audience.upper())
        service_slug = self.request.query_params.get("service_slug")
        if service_slug:
            queryset = queryset.filter(slug=service_slug)
        return queryset.order_by("subcategory__category__name", "name")


class ProfessionalServiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProfessionalServiceSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = (
            ProfessionalService.objects.filter(
                is_active=True,
                professional__is_active=True,
            )
            .select_related(
                "professional",
                "professional__user",
                "service",
                "service__subcategory",
                "service__subcategory__category",
            )
            .order_by("price")
        )

        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(service__subcategory__category__slug=category)
        audience = self.request.query_params.get("audience")
        if audience:
            queryset = queryset.filter(service__subcategory__audience=audience.upper())
        service_slug = self.request.query_params.get("service_slug")
        if service_slug:
            queryset = queryset.filter(service__slug=service_slug)

        available_now = self.request.query_params.get("available_now")
        if available_now in {"1", "true", "yes"}:
            queryset = queryset.filter(professional__is_online=True)

        return queryset


class ProfessionalServiceManageViewSet(viewsets.ModelViewSet):
    serializer_class = ProfessionalServiceManageSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if self.request.user.role != self.request.user.Role.PROFESSIONAL:
            return ProfessionalService.objects.none()
        return ProfessionalService.objects.filter(
            professional__user=self.request.user,
        ).select_related("service", "service__subcategory", "service__subcategory__category")

    def perform_create(self, serializer):
        if self.request.user.role != self.request.user.Role.PROFESSIONAL:
            raise PermissionDenied("Professional access required.")
        profile = self.request.user.professional_profile
        serializer.save(professional=profile)


class AdminCatalogView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _is_admin(self, request):
        return request.user.is_staff or request.user.role == request.user.Role.ADMIN

    def get(self, request):
        if not self._is_admin(request):
            return Response({"detail": "Administrator access required."}, status=status.HTTP_403_FORBIDDEN)
        return Response({
            "services": list(Service.objects.filter(is_active=True).values("id", "name", "duration_minutes")),
            "professional_services": [
                {"id": item.id, "professional_id": item.professional_id, "professional_name": item.professional.user.get_full_name(), "service_id": item.service_id, "service_name": item.service.name, "price": item.price, "duration_minutes": item.duration_minutes}
                for item in ProfessionalService.objects.filter(is_active=True).select_related("professional__user", "service")
            ],
        })

    def patch(self, request):
        if not self._is_admin(request):
            return Response({"detail": "Administrator access required."}, status=status.HTTP_403_FORBIDDEN)
        if "service_id" in request.data:
            service = Service.objects.get(pk=request.data["service_id"])
            service.duration_minutes = request.data["duration_minutes"]
            service.full_clean()
            service.save(update_fields=["duration_minutes"])
            ProfessionalService.objects.filter(service=service).update(duration_minutes=service.duration_minutes)
            return Response({"id": service.id, "duration_minutes": service.duration_minutes})
        professional_service = ProfessionalService.objects.get(pk=request.data["professional_service_id"])
        professional_service.price = request.data["price"]
        professional_service.full_clean()
        professional_service.save(update_fields=["price"])
        return Response({"id": professional_service.id, "price": professional_service.price})
