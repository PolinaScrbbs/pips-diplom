from django.shortcuts import render, redirect
from django.http import JsonResponse
from .forms import BookingForm

def create_booking(request):
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            form.save()
            next_url = request.POST.get("next", request.GET.get("next", "main:index"))
            try:
                return redirect(next_url)
            except:
                return redirect("main:index")
    else:
        form = BookingForm()
    # Можно вернуть JSON, если хочется для AJAX
    return JsonResponse({"ok": True})