from django.shortcuts import render

def index(request):
    services_list = [
        {'title': 'Детская психология', 'icon': 'bi-emoji-smile', 'text': 'Тревожность, страхи, трудности в школе и дома.'},
        {'title': 'Семейная терапия', 'icon': 'bi-people', 'text': 'Конфликты, адаптация к разводу или переезду.'},
        {'title': 'Помощь школьникам', 'icon': 'bi-book', 'text': 'Мотивация, выбор профессии, отношения со сверстниками.'},
        {'title': 'Развивающие группы', 'icon': 'bi-controller', 'text': 'Развитие эмоционального интеллекта и навыков общения.'},
        {'title': 'Для родителей', 'icon': 'bi-heart-pulse', 'text': 'Помощь в понимании поведения и борьба с выгоранием.'},
        {'title': 'Диагностика', 'icon': 'bi-search', 'text': 'Комплексное обследование и сопровождение в лечении.'}
    ]
    return render(request, 'main/index.html', {'services': services_list})

def why_us(request):
    return render(request, 'main/why_us.html')