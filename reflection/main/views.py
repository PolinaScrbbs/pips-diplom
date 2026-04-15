from django.shortcuts import render

def index(request):
    return render(request, "main/index.html")

def why_us(request):
    return render(request, "main/why_us.html")