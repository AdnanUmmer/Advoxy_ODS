from celery import shared_task
from django.utils import timezone

# NOTE: notification sending (Firebase/Twilio SMS) and the automated
# call (Twilio) are stubbed as function calls to be wired up when those
# integrations are added — not built here, per your instruction to only
# add what's needed to make the modeled flow real, nothing speculative.


@shared_task
def send_reaffirmation_prompt(booking_id):
    """
    Fired once, 1 hour before a SCHEDULED booking's start time (queued
    by whatever creates/confirms the booking, via apply_async(eta=...)).
    Kicks off the reminder chain if neither party has confirmed yet.
    """
    from bookings.models import Booking

    booking = Booking.objects.get(pk=booking_id)
    if booking.status != Booking.Status.AWAITING_REAFFIRMATION:
        return  # already progressed past this stage, nothing to do

    _notify_reaffirmation(booking, reminder_number=1)
    send_reaffirmation_reminder.apply_async(args=[booking_id, 2], countdown=10 * 60)


@shared_task
def send_reaffirmation_reminder(booking_id, reminder_number):
    """
    reminder_number counts 2 and 3 — the first prompt is sent by
    send_reaffirmation_prompt above. Stops escalating the moment both
    sides have confirmed.
    """
    from bookings.models import Booking

    booking = Booking.objects.get(pk=booking_id)
    if booking.reaffirmation_confirmed_by_customer and booking.reaffirmation_confirmed_by_professional:
        return  # both confirmed — chain ends here

    if reminder_number > 3:
        trigger_automated_reaffirmation_call.delay(booking_id)
        return

    _notify_reaffirmation(booking, reminder_number=reminder_number)
    send_reaffirmation_reminder.apply_async(
        args=[booking_id, reminder_number + 1], countdown=10 * 60
    )


@shared_task
def trigger_automated_reaffirmation_call(booking_id):
    """
    Section 9: "if there's still no response, an automated call is
    placed asking whether to accept or cancel." Wire this to Twilio
    Voice + a TwiML endpoint that records the accept/cancel response
    when that integration is added.
    """
    from bookings.models import Booking, BookingStatusEvent

    booking = Booking.objects.get(pk=booking_id)
    BookingStatusEvent.objects.create(
        booking=booking,
        status=booking.status,
        note=f"Automated reaffirmation call triggered — reminder_number=4 (unconfirmed party unresolved)",
    )
    # TODO: place Twilio Voice call once Twilio integration is added.


def _notify_reaffirmation(booking, reminder_number):
    """Placeholder for the actual push/SMS send (Firebase/Twilio)."""
    from bookings.models import BookingStatusEvent

    BookingStatusEvent.objects.create(
        booking=booking,
        status=booking.status,
        note=f"Reaffirmation reminder #{reminder_number} sent to unconfirmed party/parties.",
    )
