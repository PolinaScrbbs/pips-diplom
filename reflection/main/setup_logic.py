# services/setup_logic.py
import os
import random
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

    # 3. Услуги (без изменений, подгружаем или создаем)
    services_full_data = [
        {
            'name': 'Первичная диагностика',
            'short_description': 'Комплексное нейропсихологическое обследование.',
            'description': 'Глубокий анализ высших психических функций ребенка для выявления особенностей развития.',
            'duration': '60 мин',
            'price': 2500.00
        },
        {
            'name': 'Логопед-дефектолог',
            'short_description': 'Коррекция речи и запуск звукопроизношения.',
            'description': 'Индивидуальные занятия по исправлению дефектов речи, работе с дислалией и дизартрией.',
            'duration': '45 мин',
            'price': 1500.00
        },
        {
            'name': 'Детский психолог',
            'short_description': 'Помощь в эмоциональной регуляции и поведении.',
            'description': 'Работа с тревожностью, страхами и трудностями социальной адаптации ребенка.',
            'duration': '50 мин',
            'price': 2000.00
        },
        {
            'name': 'Сенсорная интеграция',
            'short_description': 'Стимуляция сенсорных систем в игровой форме.',
            'description': 'Занятия в специально оборудованном зале для развития вестибулярного аппарата и проприоцепции.',
            'duration': '45 мин',
            'price': 1800.00
        },
        {
            'name': 'Подготовка к школе',
            'short_description': 'Формирование навыков для успешного обучения.',
            'description': 'Обучение чтению, письму, счету и психологическая подготовка к школьной среде.',
            'duration': '60 мин',
            'price': 1200.00
        },
        {
            'name': 'Арт-терапия',
            'short_description': 'Творческое самовыражение и психологическая разгрузка.',
            'description': 'Использование песочной терапии, рисования и лепки для снятия эмоционального напряжения.',
            'duration': '90 мин',
            'price': 1400.00
        },
    ]
    
    for s_data in services_full_data:
        # Используем get_or_create, чтобы не дублировать услуги при повторном запуске
        obj, created = Service.objects.get_or_create(
            name=s_data['name'], 
            defaults=s_data
        )
        if not created:
            # Если услуга уже была, обновляем поля (на случай, если данные изменились)
            for key, value in s_data.items():
                setattr(obj, key, value)
            obj.save()

    print(f"✅ Услуги заполнены: {Service.objects.count()} записей.")

    # 4. Пользователи
    users_list = []
    users_info = [
        {'username': 'ivan', 'first_name': 'Иван'},
        {'username': 'marina', 'first_name': 'Марина'},
        {'username': 'elena', 'first_name': 'Елена'},
        {'username': 'dmitry', 'first_name': 'Дмитрий'},
    ]
    for u_data in users_info:
        u, created = User.objects.get_or_create(username=u_data['username'], defaults=u_data)
        if created:
            u.set_password('1')
            u.save()
        users_list.append(u)
    print("✅ Тестовые пользователи созданы.")

    # 5. Наполнение ОТЗЫВОВ под новую модель
    # Формат: (Текст, Отношение, Название услуги, Рейтинг)
    reviews_content = [
        ("Замечательный логопед! Ребенок начал выговаривать 'Р' уже через месяц.", "Мама", "Логопед-дефектолог", 5),
        ("Прошли диагностику, получили четкий план действий. Очень профессионально.", "Папа", "Первичная диагностика", 5),
        ("Дочке очень нравятся занятия арт-терапией, стала намного спокойнее.", "Мама", "Арт-терапия", 4),
        ("Сенсорная интеграция — это спасение для нашего гиперактивного сына.", "Отец", "Сенсорная интеграция", 5),
        ("Хороший центр, но иногда сложно записаться на удобное время.", "Мама", "Детский психолог", 3),
        ("Ходим на подготовку к школе, очень сильная программа.", "Бабушка", "Подготовка к школе", 5),
        ("Логопед нашел подход к самому капризному ребенку. Рекомендую!", "Мама", "Логопед-дефектолог", 5),
        ("Результаты диагностики совпали с нашими наблюдениями на 100%.", "Папа", "Первичная диагностика", 4),
    ]

    for text, rel, s_name, star in reviews_content:
        # Проверяем по полю 'text', так как поля 'content' больше нет
        if not Review.objects.filter(text=text).exists():
            service = Service.objects.filter(name=s_name).first()
            # Берем случайного пользователя из базы для автора
            random_author = random.choice(users_list)
            
            # 1. Создаем Booking (обязателен для твоей модели Review)
            booking = Booking.objects.create(
                user=random_author,
                service=service,
                child_name="Тестовый ребенок",
                parent_name=random_author.first_name,
                phone="89000000000",
            )
            
            # 2. Создаем сам отзыв по новой структуре
            Review.objects.create(
                author=random_author, # Передаем объект User
                relation=rel,
                text=text,            # Поле text вместо content
                rating=star,          # Поле rating (1-5)
                booking=booking       # Связь OneToOne
            )
    
    print(f"✅ База обновлена: {Booking.objects.count()} бронирований и {Review.objects.count()} отзывов.")
    print("--- Инициализация завершена успешно ---")