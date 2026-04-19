# services/setup_logic.py
import os
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

def run():
    from django.contrib.auth import get_user_model
    from services.models import Service
    from booking.models import Booking
    from reviews.models import Review

    User = get_user_model()
    
    print("--- Автоматическая проверка и наполнение БД ---")
    
    # 1. Проверка таблиц и миграции
    tables = connection.introspection.table_names()
    if 'services_service' not in tables:
        print("⚠️ Таблицы не найдены. Применяю миграции...")
        call_command('migrate', interactive=False)
    
    # 2. Суперпользователь 'q'
    if not User.objects.filter(username='q').exists():
        User.objects.create_superuser(username='q', password='1', email='')
        print("✅ Суперпользователь 'q' создан.")

    # 3. Расширенный список услуг
    services_data = [
        {
            'name': 'Первичная диагностика',
            'price': 2500,
            'duration': '60 мин',
            'short_description': 'Комплексное обследование нейропсихолога.',
            'description': 'Углубленное исследование высших психических функций ребенка: внимания, памяти, мышления и речи. По результатам выдается подробное заключение и рекомендации по коррекционному маршруту.'
        },
        {
            'name': 'Логопед-дефектолог',
            'price': 1500,
            'duration': '45 мин',
            'short_description': 'Коррекция звукопроизношения и развитие речи.',
            'description': 'Индивидуальные занятия по постановке звуков, развитию фонематического слуха и расширению словарного запаса. Работа с нарушениями любого уровня сложности (дислалия, дизартрия, алалия).'
        },
        {
            'name': 'Детский психолог',
            'price': 2000,
            'duration': '50 мин',
            'short_description': 'Эмоциональная поддержка и работа с поведением.',
            'description': 'Работа с детскими страхами, тревожностью, агрессивным поведением и трудностями адаптации. Помогаем ребенку понять свои эмоции и наладить контакт с окружающим миром.'
        },
        {
            'name': 'Сенсорная интеграция',
            'price': 1800,
            'duration': '45 мин',
            'short_description': 'Занятия в специально оборудованном зале.',
            'description': 'Метод коррекции, направленный на стимуляцию работы всех органов чувств. Помогает детям с нарушениями координации, гиперактивностью и проблемами восприятия информации.'
        },
        {
            'name': 'Подготовка к школе',
            'price': 1200,
            'duration': '60 мин',
            'short_description': 'Групповые занятия для будущих первоклассников.',
            'description': 'Комплексная подготовка: обучение чтению, письму, основам математики, а главное — формирование психологической готовности к школе и навыков работы в коллективе.'
        },
        {
            'name': 'Арт-терапия',
            'price': 1400,
            'duration': '90 мин',
            'short_description': 'Творческое самовыражение и снятие зажимов.',
            'description': 'Исцеление через творчество. Использование песка, красок, глины и сказкотерапии для решения внутренних конфликтов ребенка и гармонизации его психического состояния.'
        },
    ]
    
    for s_data in services_data:
        Service.objects.get_or_create(name=s_data['name'], defaults=s_data)
    print(f"✅ Услуги проверены (всего: {Service.objects.count()}).")

    # 4. Больше пользователей
    users_data = [
        {'username': 'ivan', 'first_name': 'Иван', 'last_name': 'Петров'},
        {'username': 'marina', 'first_name': 'Марина', 'last_name': 'Соколова'},
        {'username': 'elena', 'first_name': 'Елена', 'last_name': 'Волкова'},
        {'username': 'dmitry', 'first_name': 'Дмитрий', 'last_name': 'Морозов'},
    ]
    for u_data in users_data:
        u, created = User.objects.get_or_create(username=u_data['username'], defaults=u_data)
        if created:
            u.set_password('1')
            u.save()
    print("✅ Тестовые пользователи созданы.")

    # 5. Создание заявок и отзывов (минимум по 1-2 для каждой услуги для теста фильтров)
    reviews_content = [
        ("Марина", "Мама", "Замечательный логопед! Ребенок начал выговаривать 'Р' уже через месяц.", "Логопед-дефектолог"),
        ("Иван", "Папа", "Прошли диагностику, получили четкий план действий. Очень профессионально.", "Первичная диагностика"),
        ("Елена", "Мама", "Дочке очень нравятся занятия арт-терапией, стала намного спокойнее.", "Арт-терапия"),
        ("Дмитрий", "Отец", "Сенсорная интеграция — это спасение для нашего гиперактивного сына.", "Сенсорная интеграция"),
        ("Светлана", "Мама", "Лучший психологический центр в городе. Индивидуальный подход.", "Детский психолог"),
        ("Ольга", "Бабушка", "Ходим на подготовку к школе, очень сильная программа.", "Подготовка к школе"),
        ("Анна", "Мама", "Логопед нашел подход к самому капризному ребенку. Рекомендую!", "Логопед-дефектолог"),
        ("Игорь", "Папа", "Результаты диагностики совпали с нашими наблюдениями на 100%.", "Первичная диагностика"),
    ]

    for author_name, rel, text, s_name in reviews_content:
        # Проверяем, существует ли уже такой отзыв (по тексту)
        if not Review.objects.filter(content=text).exists():
            service = Service.objects.filter(name=s_name).first()
            user = User.objects.order_by('?').first() # Случайный юзер из созданных
            
            # Создаем фейковую завершенную заявку для связи с отзывом
            booking = Booking.objects.create(
                user=user,
                service=service,
                child_name="Тестовый ребенок",
                parent_name=author_name,
                phone="89000000000",
            )
            
            # Создаем сам отзыв
            Review.objects.create(
                name=author_name,
                relation=rel,
                content=text,
                booking=booking
            )
    
    print(f"✅ База наполнена: {Booking.objects.count()} заявок и {Review.objects.count()} отзывов.")
    print("--- Инициализация завершена успешно ---")