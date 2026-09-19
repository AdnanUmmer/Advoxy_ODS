from django.conf import settings
from django.db import models


class Conversation(models.Model):
    booking = models.OneToOneField("bookings.Booking", on_delete=models.CASCADE, related_name="conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    is_demo = models.BooleanField(default=False)

    @property
    def participants(self):
        return [self.booking.customer_id, self.booking.professional.user_id if self.booking.professional_id else None]


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="messages_sent")
    body = models.TextField(max_length=4000)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
