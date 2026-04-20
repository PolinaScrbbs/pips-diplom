from turtle import mode

from django.db import models
from django.db.models import Count
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from main.utils import moderator_required

from .models import Review
from .forms import ReviewCreateForm
from services.models import Service
from booking.models import Booking

def reviews(request):
    """
    Публичная страница отзывов с фильтрацией по услугам.
    """
    service_id = request.GET.get('service')
    
    # 1. Популярные услуги для фильтра (только те, у которых есть отзывы)
    popular_services = Service.objects.annotate(
        num_reviews=Count('bookings__review_link')
    ).filter(num_reviews__gt=0).order_by('-num_reviews')[:5]

    # 2. Список отзывов с оптимизацией запросов (select_related)
    # Загружаем автора и связанную услугу сразу, чтобы не перегружать БД
    review_list = Review.objects.all().select_related(
        'author', 
        'booking__service'
    ).order_by('-created_at')

    # 3. Безопасная фильтрация (защита от service=None или service=string)
    if service_id and service_id not in ['all', 'None'] and str(service_id).isdigit():
        review_list = review_list.filter(booking__service_id=service_id)
    else:
        service_id = 'all'

    # 4. Пагинация (6 отзывов на страницу)
    paginator = Paginator(review_list, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'reviews/reviews.html', {
        'page_obj': page_obj,
        'popular_services': popular_services,
        'current_service': service_id
    })


@login_required
def create_review(request):
    """
    Создание отзыва через AJAX. Только для авторизованных пользователей.
    """
    if request.method == "POST":
        booking_id = request.POST.get('booking_id')
        
        if not booking_id:
            return JsonResponse({"ok": False, "message": "ID бронирования отсутствует"}, status=400)
            
        # Проверяем, что бронь существует и принадлежит текущему пользователю
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        
        form = ReviewCreateForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.author = request.user  # Привязываем автора из сессии
            review.booking = booking      # Привязываем к конкретной записи
            review.save()
            
            return JsonResponse({
                "ok": True, 
                "message": "Спасибо! Ваш отзыв опубликован."
            })
            
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    return JsonResponse({"ok": False, "message": "Метод не поддерживается"}, status=405)

@moderator_required
def moderator_reviews_list(request):
    """
    Панель модератора: просмотр всех отзывов с фильтрами.
    """
    # Оптимизируем запрос: подтягиваем автора
    reviews_list = Review.objects.all().select_related('author').order_by('-created_at')

    # Получаем параметры поиска
    search_query = request.GET.get('search', '')
    rating_filter = request.GET.get('rating', '')
    
    # Поиск по юзернейму или тексту отзыва
    if search_query:
        reviews_list = reviews_list.filter(
            models.Q(author__username__icontains=search_query) | 
            models.Q(text__icontains=search_query)
        )

    # Фильтр по оценке (1-5 звезд)
    if rating_filter and rating_filter.isdigit():
        reviews_list = reviews_list.filter(rating=rating_filter)

    # Пагинация для модератора (10 записей)
    paginator = Paginator(reviews_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'rating_filter': rating_filter,
    }
    return render(request, 'reviews/moderator_reviews.html', context)