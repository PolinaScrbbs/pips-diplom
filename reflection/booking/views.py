# booking/views.py
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .forms import BookingForm


@login_required(login_url="users:login")
def create_booking(request):
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.save()

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True})

            return redirect(request.POST.get("next", "main:index"))
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "errors": form.errors}, status=400
                )

    return redirect("main:index")
