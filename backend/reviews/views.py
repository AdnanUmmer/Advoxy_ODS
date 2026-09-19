from rest_framework import permissions, viewsets

from accounts.models import ProfessionalProfile

from .models import Review
from .serializers import ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
	serializer_class = ReviewSerializer
	permission_classes = [permissions.IsAuthenticatedOrReadOnly]
	http_method_names = ["get", "post", "head", "options"]

	def get_queryset(self):
		user = self.request.user
		queryset = Review.objects.select_related("reviewer", "reviewee", "booking")
		professional_id = self.request.query_params.get("professional")
		if professional_id:
			professional = ProfessionalProfile.objects.filter(pk=professional_id).select_related("user").first()
			if professional is None:
				return queryset.none()
			return queryset.filter(reviewee=professional.user)
		if not user.is_authenticated:
			return queryset.none()
		if user.is_staff or user.role == user.Role.ADMIN:
			return queryset.all()
		return queryset.filter(reviewer=user) | queryset.filter(reviewee=user)
