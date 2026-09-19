from django.utils import timezone
from rest_framework import decorators, permissions, response, status, viewsets

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            booking__customer=user
        ) | Conversation.objects.filter(booking__professional__user=user)

    @decorators.action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        conversation = self.get_object()
        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = Message.objects.create(conversation=conversation, sender=request.user, body=serializer.validated_data["body"])
        return response.Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        conversation = self.get_object()
        conversation.messages.exclude(sender=request.user).filter(read_at__isnull=True).update(read_at=timezone.now())
        return response.Response({"read": True})
