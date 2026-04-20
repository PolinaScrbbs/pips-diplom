# booking/context_processors.py
from .forms import BookingForm
from services.models import Service


def booking_form_context(request):
    services = None
    last_booking = None
    if request.user.is_authenticated:
        last_booking = request.user.bookings.order_by("-created_at").first()

        if request.user.is_user():
            services = Service.objects.all()
    return {
        "booking_form": BookingForm(),
        "services": services,
        "last_booking": last_booking,
    }
