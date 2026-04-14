from django.shortcuts import render, redirect
from .forms import BookingForm

def home(request):
    return render(request, "index.html")


def services(request):
    return render(request, "services.html")


def why_us(request):
    return render(request, "why_us.html")


def reviews(request):
    return render(request, "reviews.html")


def create_booking(request):
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            form.save()

            # Возвращаемся на предыдущую страницу
            next_url = request.POST.get("next", request.GET.get("next", "main:home"))
            try:
                from django.urls import reverse
                from django.shortcuts import HttpResponseRedirect
                from django.utils.http import url_has_allowed_host_and_scheme

                # Проверяем безопасность URL
                if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    return HttpResponseRedirect(next_url)
                else:
                    return redirect(next_url)
            except:
                return redirect("main:home")

    else:
        form = BookingForm()

    return render(request, "index.html", {"booking_form": form})