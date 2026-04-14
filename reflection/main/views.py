from django.shortcuts import render


def home(request):
    return render(request, "index.html")


def services(request):
    return render(request, "services.html")


def why_us(request):
    return render(request, "why_us.html")


def reviews(request):
    return render(request, "reviews.html")
