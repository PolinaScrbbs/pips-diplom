# Отражение — центр психологической поддержки и развития ребёнка

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2.13-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4-FF6384?logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()

Веб-приложение для детского центра «Отражение» в Курске. Публичный сайт с услугами и отзывами + личный кабинет клиента + многоуровневая административная панель с аудитом действий, инспектором БД и системными логами.

---

## Содержание

- [О проекте](#о-проекте)
- [Целевая аудитория](#целевая-аудитория)
- [Технологический стек](#технологический-стек)
- [Ключевые возможности](#ключевые-возможности)
- [Быстрый старт](#быстрый-старт)
- [Конфигурация](#конфигурация)
- [Запуск](#запуск)
- [Учётные записи для тестирования](#учётные-записи-для-тестирования)
- [Структура проекта](#структура-проекта)
- [Админ-панель](#админ-панель)
- [Тестирование](#тестирование)
- [Деплой](#деплой)
- [Лицензия](#лицензия)
- [Автор](#автор)

---

## О проекте

«Отражение» — это полноценный сайт детского психологического центра, в котором:

- клиент видит каталог услуг, отзывы и блок «Почему мы»;
- зарегистрированный пользователь записывается на приём через модальное окно-форму;
- модератор управляет услугами и модерирует отзывы;
- администратор получает инструменты корпоративного уровня: журнал аудита изменений, инспектор схемы БД с ERD-диаграммой, живой лог SQL-запросов, системные логи в стиле терминала, режим имитации пользователя (Impersonation), анимированные переходы между разделами и тумблер их отключения.

Проект разработан как дипломная работа и демонстрирует полный цикл: от UI/UX и моделей данных до middleware-уровня, кастомного логирования, сигналов Django и SPA-подобных переходов между страницами.

## Целевая аудитория

| Роль | Что получает |
|------|--------------|
| **Клиент** (родитель) | Каталог услуг, запись на приём, отзывы, личный кабинет |
| **Модератор** | Управление услугами и модерация отзывов |
| **Администратор** | Пользователи, статистика, журнал аудита, системные логи, инспектор БД, Impersonation |

## Технологический стек

### Backend
- **Python 3.11+**
- **Django 5.2.13** — основной фреймворк
- **SQLite 3** — база данных из коробки (легко заменяется на PostgreSQL)
- **sqlparse** — форматирование SQL в инспекторе запросов
- **black** — форматирование кода

### Frontend
- **Bootstrap 5** + **Bootstrap Icons**
- **Chart.js 4** — графики статистики и sparkline-график SQL-запросов
- **IMask.js** — маски телефонных номеров в формах
- **Кастомные CSS-анимации** — переходы между зонами интерфейса через `clip-path`

### Архитектурные компоненты
- Ролевая модель пользователей (`admin` / `moderator` / `user`) с декораторами доступа
- Кастомный обработчик логов `DailyFolderFileHandler` — логи раскладываются по `media/logs/YYYY-MM/DD.log`
- Middleware для навигационного логирования, аудита, перехвата SQL-запросов, контекста Impersonation
- Django signals для автоматической фиксации изменений в журнале аудита
- Интроспекция ORM для построения интерактивной ERD-схемы БД

## Ключевые возможности

### Публичная часть
- Главная страница с услугами и отзывами
- Детальные страницы услуг
- Форма записи на приём (модальное окно) с маской телефона
- Регистрация и вход

### Личный кабинет клиента
- Профиль с анимированным редактированием
- История бронирований и отзывов
- Возможность оставить отзыв

### Панель модератора
- CRUD услуг (регистронезависимый поиск, в т. ч. по кириллице)
- Модерация отзывов

### Панель администратора
- **Пользователи** — таблица с ролями и безопасным удалением (админ не удалит себя и других админов)
- **Статистика** — дашборд с Chart.js (line / doughnut / bar / polar area)
- **Системные логи** — терминал с живым стримом, фильтром по пользователю и дате, архивом файлов
- **Журнал аудита** — автоматическая фиксация `create/update/delete` с пагинацией, фильтрами и модалкой diff
- **Инспектор БД** — интерактивная ERD-схема с force-directed layout, pan/zoom/drag, детальной панелью по клику
- **Живой лог SQL** — in-memory кольцевой буфер с sparkline-графиком длительности
- **Impersonation** — вход от имени любого пользователя с sticky-баннером возврата
- **Уникальные анимации переходов** между БД, Аудитом, Статистикой и Логами
- **Тумблер отключения анимаций** в навбаре (сохраняется в `localStorage`)
- Страницы ошибок 403/404 с проверкой ролей

## Быстрый старт

### Требования
- Python 3.11 или новее
- `pip` и `venv`
- Git

### Установка

```bash
git clone <url-репозитория>
cd reflection

python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Инициализация БД

Проект содержит автоматическую инициализацию при первом запуске: применяются миграции и наполняются услуги и тестовые пользователи. Вручную это выглядит так:

```bash
python manage.py migrate
python manage.py createsuperuser   # опционально — свой админ
```

## Конфигурация

По умолчанию конфигурация находится в `reflection/settings.py`. Для продакшена рекомендуется вынести секреты в переменные окружения. Пример `.env` (при использовании `django-environ` или аналога):

```bash
# Режим
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=замените-на-длинную-случайную-строку
DJANGO_ALLOWED_HOSTS=example.com,www.example.com

# База данных (необязательно, по умолчанию SQLite)
DATABASE_URL=postgres://user:pass@localhost:5432/reflection

# Логи
LOG_LEVEL=INFO
LOG_DIR=media/logs
```

> В текущей версии значения читаются напрямую из `settings.py`. Для боевого деплоя переключите `DEBUG=False`, заполните `ALLOWED_HOSTS` и замените `SECRET_KEY`.

## Запуск

```bash
source .venv/bin/activate
python manage.py runserver
```

Сайт откроется по адресу [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

При первом запуске в терминале появится сообщение об автоматическом наполнении БД:

```
--- Автоматическая проверка и наполнение БД ---
✅ Услуги заполнены: 6 записей.
✅ Тестовые пользователи созданы.
✅ База обновлена: 9 бронирований и 9 отзывов.
--- Инициализация завершена успешно ---
```

### Учётные записи для тестирования

После автоматической инициализации доступны:

| Роль | Логин | Пароль |
|------|-------|--------|
| Администратор | `q` | `q` |
| Модератор | см. Django admin → Users | — |
| Пользователь | `ivan`, `marina`, `elena`, `dmitry` | `q` |

> Пароли тестовые и годятся только для dev-среды. На проде меняйте `createsuperuser`-ом.

## Структура проекта

```
reflection/
├── manage.py
├── requirements.txt
├── db.sqlite3                    # создаётся при первом запуске
├── reflection/                   # настройки Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── main/                         # главная, публичные страницы, логирование
│   ├── log_handler.py            # DailyFolderFileHandler (логи по дням)
│   ├── middleware.py             # NavigationLoggingMiddleware
│   └── setup_logic.py            # автоматическая инициализация БД
│
├── users/                        # модель User, роли, авторизация
├── services/                     # каталог услуг + CRUD для модератора
├── reviews/                      # отзывы + модерация
├── booking/                      # запись на приём
│
├── admin_panel/                  # админ-панель
│   ├── views.py
│   ├── decorators.py             # @admin_required и пр.
│   ├── middleware.py             # QueryLogMiddleware, AuditContextMiddleware
│   ├── signals.py                # автозапись в AuditLog
│   ├── db_inspector.py           # интроспекция ORM → JSON-схема
│   └── query_log.py              # in-memory кольцевой буфер SQL
│
├── static/                       # static-файлы: vendor/, css/, js/, fonts/, images/
│   ├── css/
│   │   ├── base.css
│   │   ├── components/           # booking-modal, theme-transition, animations-toggle...
│   │   └── pages/                # admin-db, admin-stats, admin-logs, admin-audit...
│   ├── js/
│   │   ├── components/           # theme-transition.js, animations-toggle.js...
│   │   └── pages/                # admin-db.js (ERD + SQL-log), admin-stats.js...
│   ├── vendor/                   # bootstrap, chartjs, imask
│   └── images/
│
├── media/
│   └── logs/YYYY-MM/DD.log       # логи приложения, разбитые по дням
│
└── templates/                    # базовые шаблоны каждого приложения внутри templates/<app>/
```

## Админ-панель

Доступна авторизованным администраторам по адресу `/admin-panel/`:

| Раздел | URL | Описание |
|--------|-----|----------|
| Пользователи | `/admin-panel/users/` | Таблица, роли, удаление, Impersonation |
| Статистика | `/admin-panel/stats/` | Графики Chart.js |
| Системные логи | `/admin-panel/logs/` | Live-терминал, фильтры, история файлов |
| Журнал аудита | `/admin-panel/audit/` | Пагинация + фильтры + diff |
| База данных | `/admin-panel/db/` | ERD-схема + живой лог SQL |

### Пример: запуск импрессонации

1. Откройте `/admin-panel/users/`.
2. Нажмите кнопку «Войти от имени» напротив пользователя.
3. Просматривайте сайт как этот пользователь — сверху видна полоса с кнопкой «Выйти из режима».

### Пример: экспорт события в журнал аудита

Любой `pre_save`, `post_save` и `post_delete` у зарегистрированных моделей создаёт запись:

```python
# admin_panel/signals.py
@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    if _should_audit(sender):
        AuditLog.objects.create(
            action="create" if created else "update",
            entity_type=sender.__name__,
            entity_id=instance.pk,
            actor=_current_actor(),
            diff=_collect_diff(instance),
        )
```

## Тестирование

Каждое приложение имеет свой `tests.py`. Запуск всего набора:

```bash
python manage.py test
```

Точечный запуск:

```bash
python manage.py test users
python manage.py test admin_panel.tests.AuditLogTests
```

Проверка конфигурации Django без запуска сервера:

```bash
python manage.py check
```

## Деплой

Для продакшена рекомендуется:

1. Переключить `DEBUG=False` и настроить `ALLOWED_HOSTS`.
2. Заменить `SECRET_KEY` на секрет из переменных окружения.
3. Перейти на PostgreSQL (опционально), заменив блок `DATABASES` в `settings.py`.
4. Собрать статику:

   ```bash
   python manage.py collectstatic --noinput
   ```

5. Запускать через **gunicorn** + **nginx**:

   ```bash
   gunicorn reflection.wsgi:application --bind 0.0.0.0:8000 --workers 3
   ```

6. Для systemd-сервиса пример unit-файла можно взять из официальной документации Django.

Альтернатива — контейнеризация. Минимальный `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "reflection.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## Лицензия

Проект распространяется по лицензии **MIT**. Полный текст — в файле `LICENSE` (добавьте при необходимости).

## Автор

- **Дипломный проект**, 2026
- Вопросы и пожелания — через Issues в репозитории или по контактам центра:
  - Адрес: г. Курск, ул. Карла Маркса, 72/20
  - Телефон: +7 (961) 168-97-98

---

<sub>Сделано с ❀ на Django 5.2</sub>
