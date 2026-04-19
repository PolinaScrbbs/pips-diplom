from django.db.models import Count
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from reviews.forms import ReviewCreateForm
from reviews.models import Review
from services.models import Service
from booking.models import Booking


from django.db.models import Count
from django.core.paginator import Paginator
from reviews.models import Review
from services.models import Service

def reviews(request):
    service_id = request.GET.get('service')
    
    # 1. Популярные услуги (Тут используем 'bookings', так как идем ОТ Service)
    # Поле 'review_link' берем из related_name в вашей модели Review
    popular_services = Service.objects.annotate(
        num_reviews=Count('bookings__review_link')
    ).filter(num_reviews__gt=0).order_by('-num_reviews')[:5]

    # 2. Список отзывов (Тут используем 'booking', так как это имя поля в модели Review)
    review_list = Review.objects.all().select_related('booking__service').order_by('-created_at')

    # 3. Фильтрация
    if service_id and service_id != 'all':
        review_list = review_list.filter(booking__service_id=service_id)

    # 4. Пагинация
    paginator = Paginator(review_list, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'reviews/reviews.html', {
        'page_obj': page_obj,
        'popular_services': popular_services,
        'current_service': service_id
    })


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