# booking/context_processors.py
from .forms import BookingForm

def booking_form_context(request):
    return {
        'booking_form': BookingForm()
    }