from django.db.models import Avg
from rest_framework import serializers

from bookings.models import Booking

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.get_full_name", read_only=True)
    customer_name = serializers.CharField(source="reviewer.get_full_name", read_only=True)
    reviewee_name = serializers.CharField(source="reviewee.get_full_name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id", "booking", "reviewer", "reviewer_name", "customer_name", "reviewee", "reviewee_name",
            "rating", "comment", "flagged_for_admin", "created_at",
        ]
        read_only_fields = ["id", "reviewer", "reviewee", "flagged_for_admin", "created_at"]

    def validate(self, attrs):
        request = self.context["request"]
        booking = attrs["booking"]
        if booking.status != Booking.Status.CONFIRMED_COMPLETE:
            raise serializers.ValidationError("Reviews are available after the customer confirms completion.")
        if request.user.id not in {booking.customer_id, booking.professional.user_id if booking.professional_id else None}:
            raise serializers.ValidationError("Only booking participants can leave a review.")
        reviewee = booking.professional.user if request.user.id == booking.customer_id else booking.customer
        if Review.objects.filter(booking=booking, reviewer=request.user).exists():
            raise serializers.ValidationError("You have already reviewed this booking.")
        attrs["reviewee"] = reviewee
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        review = Review.objects.create(reviewer=request.user, **validated_data)
        professional = review.booking.professional
        if professional:
            received = Review.objects.filter(reviewee=professional.user)
            professional.review_count = received.count()
            professional.average_rating = received.aggregate(Avg("rating")).get("rating__avg")
            professional.save(update_fields=["review_count", "average_rating"])
        return review
