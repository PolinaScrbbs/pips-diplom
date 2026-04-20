# booking/context_processors.py
from .forms import BookingForm


def booking_form_context(request):
    last_booking = None
    if request.user.is_authenticated:
        last_booking = request.user.bookings.order_by("-created_at").first()
    return {"booking_form": BookingForm(), "last_booking": last_booking}
