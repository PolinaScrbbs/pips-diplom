from django.core.management.base import BaseCommand
from reviews.models import Review

REVIEWS = [
    {
        "name": "Ольга",
        "relation": "мама 8‑летнего сына",
        "content": (
            "После работы с психологом у ребёнка заметно уменьшилась тревожность. "
            "Стало видно легче и спокойнее ему и нам в семье."
        ),
    },
    {
        "name": "Анна",
        "relation": "мама 12‑летней дочери",
        "content": (
            "Ребёнок перестал замыкаться в себе и начала говорить о своих переживаниях. "
            "Конфликты с одноклассниками и учителями стали заметно реже. "
            "Сейчас она намного спокойнее и увереннее."
        ),
    },
    {
        "name": "Виктор",
        "relation": "папа 10‑летнего сына",
        "content": (
            "Раньше я не понимал, как правильно общаться с сыном. Сейчас научились говорить спокойно, "
            "а ребёнок перестал бояться, что каждую фразу воспринимают как «выговор»."
        ),
    },
    {
        "name": "Мария",
        "relation": "мама 6‑летней дочери",
        "content": (
            "Дочь раньше стеснялась детей, боялась утренников. С психологом мы постепенно работали "
            "с её тревожностью, а сейчас она активно участвует в группах и даже предлагает идеи для игр."
        ),
    },
    {
        "name": "Наталья",
        "relation": "мама 14‑летнего подростка",
        "content": (
            "Подростковый возраст даётся тяжело. Психолог помогает не только сыну, но и нам, "
            "родителям, понять, что он переживает и почему ведёт себя так, а не иначе."
        ),
    },
    {
        "name": "Игорь",
        "relation": "отец двоих детей",
        "content": (
            "Семейные консультации помогли нам перестать кричать на детей и научиться "
            "слушать их. Семья стала более спокойной, даже мелкие конфликты теперь "
            "разбираем без слёз и угроз."
        ),
    },
]


class Command(BaseCommand):
    help = "Загружает тестовые отзывы (если ещё нет)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Удалить все существующие отзывы и загрузить заново",
        )

    def handle(self, *args, **options):
        force = options["force"]

        if force:
            Review.objects.all().delete()
            self.stdout.write("Все существующие отзывы удалены.")

        existing_names = set(Review.objects.values_list("name", flat=True))

        added = 0
        for data in REVIEWS:
            if data["name"] in existing_names:
                self.stdout.write(
                    f"Отзыв от '{data['name']}' уже есть в базе. Пропускаем."
                )
                continue

            Review.objects.create(
                name=data["name"],
                relation=data["relation"],
                content=data["content"],
            )
            added += 1

        self.stdout.write(
            self.style.SUCCESS(f"Добавлено {added} новых отзывов.")
        )
        self.stdout.write(
            f"Общее количество отзывов в БД: {Review.objects.count()}"
        )