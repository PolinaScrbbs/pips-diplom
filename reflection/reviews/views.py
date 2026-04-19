from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from reviews.forms import ReviewCreateForm
from reviews.models import Review
from booking.models import Booking


def reviews(request):
    review_list = Review.objects.all()
    return render(
        request,
        "reviews/reviews.html",
        {"review_list": review_list},
    )


def create_review(request):
    if request.method == "POST":
        booking_id = request.POST.get('booking_id')
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        
        form = ReviewCreateForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking # Прямая привязка к записи
            review.save()
            
            # Сохраняем обратную связь в модели Booking, если у вас OneToOneField
            booking.review = review
            booking.save()
            
            return JsonResponse({"ok": True, "message": "Отзыв успешно добавлен!"})
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)