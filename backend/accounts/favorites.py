from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FavoriteProfessional, ProfessionalProfile, User
from .serializers import ProfessionalProfileSerializer


class FavoriteProfessionalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        favorites = FavoriteProfessional.objects.filter(customer=request.user).select_related("professional__user")
        professionals = [favorite.professional for favorite in favorites]
        return Response(ProfessionalProfileSerializer(professionals, many=True, context={"request": request}).data)

    def post(self, request, professional_id):
        if request.user.role != User.Role.CUSTOMER:
            return Response({"detail": "Only customer accounts can save favorites."}, status=status.HTTP_403_FORBIDDEN)
        professional = ProfessionalProfile.objects.filter(pk=professional_id, is_active=True).first()
        if professional is None:
            return Response({"detail": "Professional not found."}, status=status.HTTP_404_NOT_FOUND)
        favorite, created = FavoriteProfessional.objects.get_or_create(customer=request.user, professional=professional)
        return Response({"professional": professional.id, "favorite": True, "created": created}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request, professional_id):
        FavoriteProfessional.objects.filter(customer=request.user, professional_id=professional_id).delete()
        return Response({"professional": professional_id, "favorite": False})
