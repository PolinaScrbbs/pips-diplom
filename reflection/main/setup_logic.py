import os
import random
import string
from dataclasses import dataclass
from datetime import timedelta

from django.core.management import call_command
from django.db import connection
from django.utils import timezone


SEED_MARKER = "[DEMO_SEED_2026]"


@dataclass(frozen=True)
class DemoUserSpec:
    username: str
    first_name: str
    role: str


def _rand_phone() -> str:
    return "7" + "".join(random.choice(string.digits) for _ in range(10))


def _backdate(model_cls, pk: int, dt):
    model_cls.objects.filter(pk=pk).update(created_at=dt)


def _write_demo_error_logs(*, count: int = 8):
    try:
        from django.conf import settings
    except Exception:
        return

    now = timezone.now()
    d = timezone.localdate()
    path = settings.APP_LOG_DIR / d.strftime("%Y-%m") / (d.strftime("%d") + ".log")
    path.parent.mkdir(parents=True, exist_ok=True)

    samples = [
        "Не удалось отправить уведомление клиенту: phone=+7 (999) 111-22-33",
        "Ошибка интеграции оплаты: token=sk_test_123456",
        "Сбой при сохранении отзыва: email=test@example.com",
        "Таймаут при загрузке страницы статистики (simulated)",
        "Ошибка валидации формы записи: phone=8-900-000-00-00",
        "Непредвиденная ошибка на странице DB inspector (simulated)",
    ]
    lines = []
    for i in range(count):
        ts = (now - timedelta(minutes=10 - i)).strftime("%Y-%m-%d %H:%M:%S")
        msg = random.choice(samples)
        msg = f"[q/admin] {msg} {SEED_MARKER}"
        lines.append(f"{ts} | ERROR   | app.admin          | {msg}")
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run():
    from django.contrib.auth import get_user_model
    from services.models import Service
    from booking.models import Booking
    from reviews.models import Review
    from admin_panel.models import AuditLog

    User = get_user_model()

    print("--- Автоматическая проверка и наполнение БД ---")

    # 1. Миграции (на всякий случай всегда, чтобы подтянуть новые таблицы/поля)
    # Для демо-скрипта это ок: migrate идемпотентен.
    call_command("migrate", interactive=False, verbosity=0)

    # 2. Админ 'q' (нужен role='admin' для admin_panel)
    q, created_q = User.objects.get_or_create(username="q", defaults={"first_name": "Админ"})
    if created_q:
        q.set_password("1")
    q.role = getattr(User, "ADMIN", "admin")
    q.is_superuser = True
    q.is_staff = True
    q.is_active = True
    q.save()
    print("✅ Админ для демо: q / 1")

    # Модератор для демо
    mod, created_mod = User.objects.get_or_create(
        username="moderator",
        defaults={"first_name": "Модератор"},
    )
    if created_mod:
        mod.set_password("1")
    mod.role = getattr(User, "MODERATOR", "moderator")
    mod.is_staff = True
    mod.is_active = True
    mod.save()
    print("✅ Модератор для демо: moderator / 1")

    # 3. Услуги (без изменений, подгружаем или создаем)
    services_full_data = [
        {
            "name": "Первичная диагностика",
            "short_description": "Комплексное нейропсихологическое обследование.",
            "description": (
                "Первичная диагностика — это комплексная встреча, на которой специалист бережно собирает информацию о развитии ребёнка "
                "и помогает родителям понять, в чём сильные стороны, а где нужна поддержка.\n\n"
                "Мы оцениваем нейропсихологию базовых навыков: внимание, память, самоконтроль и особенности обучения. "
                "По итогам вы получаете понятный план: что делать дома, какие навыки развивать и какие занятия подойдут именно вашему ребёнку.\n\n"
                "Особое внимание уделяем школьной готовности: как ребёнок воспринимает инструкции, удерживает задачу и переносит нагрузку.\n\n"
                "Ключевые слова: нейропсихология, внимание, память, диагностика, школьная готовность"
            ),
            "duration": "60 мин",
            "price": 2500.00,
        },
        {
            "name": "Логопед-дефектолог",
            "short_description": "Коррекция речи и запуск звукопроизношения.",
            "description": (
                "Занятия с логопедом‑дефектологом помогают ребёнку развить чёткую, понятную речь и уверенность в общении.\n\n"
                "Мы работаем со звукопроизношением, дыханием, артикуляцией и пониманием речи. "
                "Тренируем фонематический слух — умение различать похожие звуки на слух — и постепенно расширяем словарь.\n\n"
                "Программа подбирается по возрасту и запросу: от постановки отдельных звуков до развития связной речи.\n\n"
                "Ключевые слова: звукопроизношение, фонематический слух, артикуляция, словарь"
            ),
            "duration": "45 мин",
            "price": 1500.00,
        },
        {
            "name": "Детский психолог",
            "short_description": "Помощь в эмоциональной регуляции и поведении.",
            "description": (
                "Детский психолог помогает ребёнку справляться с трудными эмоциями и ситуациями — от школьной тревожности до конфликтов со сверстниками.\n\n"
                "На встречах мы учимся понимать чувства, безопасно выражать злость, снижать страхи и укреплять самооценку. "
                "При необходимости работаем с адаптацией к детскому саду/школе и навыками общения.\n\n"
                "Родители получают рекомендации, как поддерживать ребёнка дома, обсуждать эмоции и выстраивать спокойные границы.\n\n"
                "Ключевые слова: тревожность, страхи, самооценка, адаптация, эмоции"
            ),
            "duration": "50 мин",
            "price": 2000.00,
        },
        {
            "name": "Сенсорная интеграция",
            "short_description": "Стимуляция сенсорных систем в игровой форме.",
            "description": (
                "Сенсорная интеграция — это занятия в игровой форме, которые помогают мозгу «правильно обрабатывать» ощущения от тела и окружающего мира.\n\n"
                "Мы развиваем координацию, телесную осознанность и саморегуляцию: ребёнку становится легче успокаиваться и переключаться.\n\n"
                "Такая работа особенно полезна при гиперактивности, повышенной чувствительности к шумам/свету/прикосновениям и трудностях с удержанием внимания.\n\n"
                "Ключевые слова: сенсорная интеграция, гиперактивность, саморегуляция, координация"
            ),
            "duration": "45 мин",
            "price": 1800.00,
        },
        {
            "name": "Подготовка к школе",
            "short_description": "Формирование навыков для успешного обучения.",
            "description": (
                "Подготовка к школе — это не только чтение и счёт, но и развитие навыков, которые помогают учиться без слёз и перегрузки.\n\n"
                "Мы тренируем чтение, письмо и счёт, а также внимание, усидчивость и мотивацию. "
                "Результат — более спокойный старт в школе и меньше конфликтов из‑за домашних заданий.\n\n"
                "Занятия проходят в темпе ребёнка: короткие шаги, много поддержки и понятные домашние рекомендации.\n\n"
                "Ключевые слова: чтение, письмо, счет, внимание, усидчивость, мотивация"
            ),
            "duration": "60 мин",
            "price": 1200.00,
        },
        {
            "name": "Арт-терапия",
            "short_description": "Творческое самовыражение и психологическая разгрузка.",
            "description": (
                "Арт‑терапия помогает ребёнку выражать чувства через творчество, когда словами это сделать трудно.\n\n"
                "Мы используем рисунок, лепку и элементы песочной терапии, чтобы поддержать самовыражение и снять стресс. "
                "В процессе ребёнок учится замечать эмоции, говорить о них и лучше выстраивать коммуникацию.\n\n"
                "Формат подходит детям, которые переживают сильные эмоции, стесняются говорить или быстро замыкаются.\n\n"
                "Ключевые слова: арт-терапия, самовыражение, стресс, эмоции, коммуникация"
            ),
            "duration": "90 мин",
            "price": 1400.00,
        },
    ]

    for s_data in services_full_data:
        # Используем get_or_create, чтобы не дублировать услуги при повторном запуске
        obj, created = Service.objects.get_or_create(
            name=s_data["name"], defaults=s_data
        )
        if not created:
            # Если услуга уже была, обновляем поля (на случай, если данные изменились)
            for key, value in s_data.items():
                setattr(obj, key, value)
            obj.save()
        # Ключевые слова теперь живут прямо в description и подсвечиваются при рендере.

    print(f"✅ Услуги заполнены: {Service.objects.count()} записей.")

    # 4. Пользователи (демо-пул)
    demo_users = []
    base_specs = [
        DemoUserSpec("ivan", "Иван", getattr(User, "USER", "user")),
        DemoUserSpec("marina", "Марина", getattr(User, "USER", "user")),
        DemoUserSpec("elena", "Елена", getattr(User, "USER", "user")),
        DemoUserSpec("dmitry", "Дмитрий", getattr(User, "USER", "user")),
    ]
    for spec in base_specs:
        u, created = User.objects.get_or_create(
            username=spec.username, defaults={"first_name": spec.first_name}
        )
        if created:
            u.set_password("1")
        u.role = spec.role
        u.is_active = True
        u.phone = u.phone or _rand_phone()
        u.save()
        demo_users.append(u)

    for i in range(1, 26):
        username = f"demo_user_{i:03d}"
        u, created = User.objects.get_or_create(
            username=username,
            defaults={"first_name": f"Демо{i:02d}"},
        )
        if created:
            u.set_password("1")
        u.role = getattr(User, "USER", "user")
        u.phone = u.phone or _rand_phone()
        u.is_active = True
        u.save()
        demo_users.append(u)
    print(f"✅ Клиенты для демо: {len(demo_users)} пользователей (пароль у всех: 1).")

    # 5. Записи + отзывы (живые распределения для статистики)
    if Booking.objects.filter(comment__icontains=SEED_MARKER).exists():
        print("ℹ️ Демо-данные уже есть (найден маркер). Пропускаю генерацию записей/отзывов.")
        print(f"✅ В базе сейчас: {Booking.objects.count()} записей и {Review.objects.count()} отзывов.")
        print("--- Инициализация завершена успешно ---")
        return

    child_names = ["Артём", "София", "Миша", "Алина", "Кирилл", "Полина", "Егор", "Вика", "Никита", "Лиза"]
    parent_names = ["Ольга", "Анна", "Ирина", "Марина", "Елена", "Наталья", "Сергей", "Игорь", "Дмитрий", "Алексей"]
    relations = ["Мама", "Папа", "Бабушка", "Опекун"]

    services = list(Service.objects.all())
    if not services:
        raise RuntimeError("Нет услуг в базе — сидер не может создать записи.")

    now = timezone.now()
    days_back = 95

    def daily_bookings_target(day_index_from_start: int) -> int:
        t = day_index_from_start / max(1, (days_back - 1))
        base = 1 + int(3 * t)
        noise = random.choice([0, 0, 1, 2, -1])
        if 0.78 <= t <= 0.83:
            base = max(0, base - 2)
        return max(0, base + noise)

    created_bookings = 0
    created_reviews = 0

    for i in range(days_back):
        day = now - timedelta(days=(days_back - 1 - i))
        n = daily_bookings_target(i)
        for _ in range(n):
            user = random.choice(demo_users)
            service = random.choice(services)

            hour = random.choice([9, 10, 11, 12, 13, 15, 17, 18, 19, 20])
            minute = random.choice([0, 10, 20, 30, 40, 50])
            dt = day.replace(hour=hour, minute=minute, second=random.randint(0, 50), microsecond=0)

            comment = random.choice([
                f"Нужно подобрать удобное время. {SEED_MARKER}",
                f"Ребёнок стесняется, важен мягкий подход. {SEED_MARKER}",
                f"Пожелание: консультация после школы. {SEED_MARKER}",
                f"Контакт: email=test@example.com, phone=+7 (999) 111-22-33. {SEED_MARKER}",
                f"{SEED_MARKER}",
            ])

            b = Booking.objects.create(
                user=user,
                service=service,
                child_name=random.choice(child_names),
                parent_name=random.choice(parent_names),
                phone=_rand_phone(),
                comment=comment,
            )
            _backdate(Booking, b.pk, dt)
            created_bookings += 1

            if random.random() < 0.55:
                rating = random.choices([5, 4, 3, 2, 1], weights=[55, 20, 12, 8, 5], k=1)[0]
                theme = random.choice([
                    "всё понравилось, специалист внимательный",
                    "сложно записаться на удобное время",
                    "не хватило объяснений, хотелось больше конкретики",
                    "ребёнку стало спокойнее после 2-х занятий",
                    "дороговато, но эффект заметен",
                    "первое занятие прошло тяжело, ребёнок плакал",
                ])
                pii_tail = ""
                if rating <= 2:
                    pii_tail = " email=badcase@example.com phone=8-900-000-00-00"

                r = Review.objects.create(
                    author=user,
                    relation=random.choice(relations),
                    text=f"{theme}.{pii_tail} {SEED_MARKER}",
                    rating=rating,
                    booking=b,
                )
                _backdate(Review, r.pk, dt + timedelta(hours=random.choice([1, 2, 5, 24])))
                created_reviews += 1

    print(f"✅ Создано демо-записей: {created_bookings}, демо-отзывов: {created_reviews}.")

    # 6. Немного audit для демонстрации
    AuditLog.objects.create(
        actor=q,
        actor_username=q.username,
        actor_role=q.role,
        action=AuditLog.ACTION_UPDATE,
        entity_type="service",
        entity_id=services[0].pk,
        entity_repr=str(services[0])[:255],
        changes={
            "price": {"before": "1200.00", "after": "1300.00"},
            "is_hidden": {"before": False, "after": False},
        },
    )

    # 7. ERROR логи для daily brief
    _write_demo_error_logs(count=10)

    print(f"✅ База обновлена: {Booking.objects.count()} бронирований и {Review.objects.count()} отзывов.")
    print("--- Инициализация завершена успешно ---")
