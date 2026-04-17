from django.shortcuts import render, redirect
from django.http import JsonResponse
from reviews.forms import SimpleReviewForm, ReviewCreateForm
from reviews.models import Review


def reviews(request):
    review_list = Review.objects.all()
    # форма для модалки «отзыв к заказу» на странице reviews
    form = ReviewCreateForm()
    return render(
        request,
        "reviews/reviews.html",
        {"review_list": review_list, "form": form},
    )


def create_simple_review(request):
    if request.method == "POST":
        form = SimpleReviewForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse(
                {"ok": True, "message": "Отзыв добавлен на сайт."},
            )
        else:
            return JsonResponse(
                {"ok": False, "errors": form.errors},
                status=400,
            )

    form = SimpleReviewForm()
    return render(
        request,
        "reviews/includes/_simple_review_form.html",
        {"form": form},
    )


def create_review(request):
    if request.method == "POST":
        form = ReviewCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse(
                {"ok": True, "message": "Отзыв к заказу успешно добавлен."},
            )
        else:
            return JsonResponse(
                {"ok": False, "errors": form.errors},
                status=400,
            )

    form = ReviewCreateForm()
    return render(
        request,
        "reviews/includes/_review_form.html",
        {"form": form},
    )