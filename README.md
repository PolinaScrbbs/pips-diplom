<p align="center">
  <img src="https://img.shields.io/badge/Отражение-психологический_центр-2d5a3d?style=for-the-badge&labelColor=1a3d27" alt="Отражение"/>
</p>

<h1 align="center">Отражение</h1>

<p align="center">
  <em>Веб-платформа для записи, отзывов и управления центром детской психологии</em><br/>
  <sub>Курск · дипломный проект · 2026</sub>
</p>

<p align="center">
  <a href="#about"><img src="https://img.shields.io/badge/документация-555?style=flat-square&logo=readthedocs&logoColor=white" alt="docs"/></a>
  <img src="https://img.shields.io/badge/Django-5.x-092E20?style=flat-square&logo=django&logoColor=white" alt="Django"/>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
</p>

---

> **В двух словах:** монолит на **Django 5** с разделением ролей, **журналом аудита**, **инспектором БД (ERD)** и опциональной **нейросетью Ollama** на своей инфраструктуре — без лишнего внешнего SaaS для типового сценария.

### В чём сила проекта

| | |
|:--|:--|
| **Наблюдаемость** | Файловые логи по дням, live SQL у админа, **Audit Log** с диффом |
| **Модель данных** | ERD и связи **из ORM** — схема не «отстаёт» от кода |
| **Продукт** | Impersonation, статистика Chart.js, **LLM-подсказки** по терминам на карточке услуги |

---

<p align="center">
  <a href="#about">О проекте</a> &nbsp;·&nbsp;
  <a href="#audience">Аудитория</a> &nbsp;·&nbsp;
  <a href="#stack">Стек</a> &nbsp;·&nbsp;
  <a href="#features">Возможности</a> &nbsp;·&nbsp;
  <a href="#quickstart">Старт</a> &nbsp;·&nbsp;
  <a href="#config">ENV</a> &nbsp;·&nbsp;
  <a href="#deploy">Деплой</a> &nbsp;·&nbsp;
  <a href="#license"><strong>MIT</strong></a> · <a href="LICENSE">LICENSE</a>
</p>

<p align="center"><strong>Используемые технологии</strong> <sub>(иконки — shields.io)</sub></p>
<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/></a>
  <a href="https://www.djangoproject.com/"><img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django"/></a>
  <a href="https://www.sqlite.org/"><img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite"/></a>
  <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5"/>
  <img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3"/>
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript"/>
  <a href="https://getbootstrap.com/"><img src="https://img.shields.io/badge/Bootstrap-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white" alt="Bootstrap"/></a>
  <a href="https://www.chartjs.org/"><img src="https://img.shields.io/badge/Chart.js-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white" alt="Chart.js"/></a>
  <img src="https://img.shields.io/badge/Bootstrap_Icons-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white" alt="Bootstrap Icons"/>
  <img src="https://img.shields.io/badge/IMask.js-242424?style=for-the-badge&logo=javascript&logoColor=F7DF1E" alt="IMask.js"/>
</p>
<p align="center">
  <a href="https://ollama.com/"><img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama"/></a>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/nginx-009639?style=for-the-badge&logo=nginx&logoColor=white" alt="nginx"/>
  <img src="https://img.shields.io/badge/LetsEncrypt-003A70?style=for-the-badge&logo=letsencrypt&logoColor=white" alt="Lets Encrypt"/>
  <img src="https://img.shields.io/badge/Certbot-003A70?style=for-the-badge&logo=letsencrypt&logoColor=white" alt="Certbot"/>
  <img src="https://img.shields.io/badge/Gunicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white" alt="Gunicorn"/>
  <a href="https://git-scm.com/"><img src="https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white" alt="Git"/></a>
</p>
<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT — см. файл LICENSE"/></a>
  <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code_style-black-000000?style=for-the-badge&logo=python&logoColor=white" alt="black"/></a>
  <img src="https://img.shields.io/badge/status-active-success?style=for-the-badge" alt="status"/>
</p>

<p align="center">
  <sub>Скриншоты интерфейса можно добавить сюда: <code>docs/screenshots/</code> → вставьте превью ниже бейджей.</sub>
</p>

<!-- Placeholder превью (замените на свои изображения)
<p align="center">
  <img src="docs/screenshots/admin-dashboard.png" alt="Админ-панель" width="48%" />
  &nbsp;
  <img src="docs/screenshots/public-home.png" alt="Главная" width="48%" />
</p>
-->

---

## Содержание

| | Раздел | Описание |
|--|--------|----------|
| 📌 | [О проекте](#about) | Цели и границы системы |
| 👥 | [Целевая аудитория](#audience) | Роли |
| 🧰 | [Технологический стек](#stack) | Backend, frontend, DevOps |
| ✨ | [Ключевые возможности](#features) | Сайт, ЛК, модератор, админ |
| 🚀 | [Быстрый старт](#quickstart) | Клонирование и venv |
| ⚙️ | [Конфигурация](#config) | Переменные окружения |
| ▶️ | [Запуск](#run) | Dev-сервер |
| 🔑 | [Учётные записи для тестирования](#accounts) | Тестовые логины |
| 📁 | [Структура проекта](#structure) | Дерево каталогов |
| 🎛️ | [Админ-панель](#admin) | Маршруты и функции |
| 🧪 | [Тестирование](#testing) | Команды тестов |
| 🚢 | [Деплой](#deploy) | Docker / Gunicorn |
| 📜 | [Лицензия](#license) | MIT |
| ✉️ | [Автор](#author) | Контакты |

---

<a id="about"></a>

## 📌 О проекте

Монолитное веб-приложение на **Django 5** для центра «Отражение» (г. Курск): публичный сайт, личный кабинет, панели **модератора** и **администратора**. По умолчанию — **SQLite**; сессии и авторизация — стандарт Django.

| Зона | Что внутри |
|------|------------|
| **Публичная** | Услуги, отзывы, запись на приём |
| **Клиент** | Профиль, бронирования, отзывы |
| **Модератор** | CRUD услуг, модерация отзывов |
| **Администратор** | Пользователи, статистика, **Audit Log**, ERD, SQL-лог, системные логи, **Impersonation** |

Наблюдаемость и контроль изменений — через middleware, сигналы и журнал аудита **без обязательного внешнего SaaS**.

Проект — дипломная работа: сквозной цикл от моделей и шаблонов до middleware, логирования и аудита.

---

<a id="audience"></a>

## 👥 Целевая аудитория

| Роль | Функциональность |
|------|------------------|
| **Клиент** | Каталог, запись, отзывы, личный кабинет |
| **Модератор** | Услуги и модерация отзывов |
| **Администратор** | Пользователи, аналитика, аудит, логи, схема БД, Impersonation |

---

<a id="stack"></a>

## 🧰 Технологический стек

<p align="left">
  <strong>Кратко с иконками:</strong>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/></a>
  <a href="https://www.djangoproject.com/"><img src="https://img.shields.io/badge/Django-092E20?style=flat-square&logo=django&logoColor=white" alt="Django"/></a>
  <img src="https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white" alt="SQLite"/>
  <img src="https://img.shields.io/badge/sqlparse-4479A1?style=flat-square&logo=sqlite&logoColor=white" alt="sqlparse"/>
  <img src="https://img.shields.io/badge/Gunicorn-499848?style=flat-square&logo=gunicorn&logoColor=white" alt="Gunicorn"/>
  <img src="https://img.shields.io/badge/black-000000?style=flat-square&logo=python&logoColor=white" alt="black"/>
  <img src="https://img.shields.io/badge/Bootstrap-7952B3?style=flat-square&logo=bootstrap&logoColor=white" alt="Bootstrap"/>
  <img src="https://img.shields.io/badge/Chart.js-FF6384?style=flat-square&logo=chartdotjs&logoColor=white" alt="Chart.js"/>
  <img src="https://img.shields.io/badge/Ollama-000000?style=flat-square&logo=ollama&logoColor=white" alt="Ollama"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/nginx-009639?style=flat-square&logo=nginx&logoColor=white" alt="nginx"/>
</p>

### Backend

| Технология | Назначение |
|------------|------------|
| Python 3.11+ | Runtime |
| Django 5.2.x | MTV, ORM, шаблоны |
| SQLite 3 | БД по умолчанию (при необходимости — PostgreSQL) |
| sqlparse | Форматирование SQL в UI |
| black | Стиль кода |

### Frontend

| Технология | Назначение |
|------------|------------|
| Bootstrap 5 + Icons | Вёрстка и иконки |
| Chart.js 4 | Дашборды, sparkline для SQL |
| IMask.js | Маски телефона |
| CSS (`clip-path` и др.) | Анимации зон интерфейса |

### DevOps и поставка

| Технология | Назначение |
|------------|------------|
| Docker / Compose | `web`, `nginx`, `ollama`, `certbot` |
| nginx | Reverse proxy, TLS, `/static/` и `/media/` в проде |
| Let’s Encrypt | TLS (`reflection/deploy/`) |

### Архитектурные акценты

- **RBAC** — `user` / `moderator` / `admin`, декораторы.
- **Логирование** — `DailyFolderFileHandler` → `media/logs/YYYY-MM/DD.log`.
- **Middleware** — навигация, контекст аудита, SQL-трейс для админских запросов.
- **Сигналы** — записи в журнал аудита при изменении сущностей.
- **Introspection** — граф для ERD из метаданных ORM.

---

<a id="features"></a>

## ✨ Ключевые возможности

### Публичная часть

- Главная, каталог услуг, отзывы, блок доверия.
- Карточки услуг и детальные страницы.
- Запись через модальное окно с маской телефона.
- Регистрация и вход.

### Личный кабинет клиента

- Профиль, история бронирований и отзывов, создание отзыва.

### Панель модератора

- CRUD услуг (поиск с учётом кириллицы).
- Модерация отзывов.

### Панель администратора

| Модуль | Описание |
|--------|----------|
| Пользователи | Роли, безопасное удаление |
| Статистика | Chart.js: line, doughnut, bar, polar |
| Системные логи | Файлы логов, фильтры |
| Журнал аудита | События, фильтры, **diff** в модалке |
| Инспектор БД | **ERD**, pan/zoom, детали узла |
| Живой лог SQL | Буфер, sparkline длительности |
| Impersonation | Вход от имени пользователя |

---

<a id="quickstart"></a>

## 🚀 Быстрый старт

**Нужно:** Python **3.11+**, Git, `pip`, `venv`.

Рабочий каталог приложения — **`reflection/`** внутри репозитория:

```bash
git clone <URL-репозитория>
cd diplom-tets/reflection

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

При первом запуске может отработать автоинициализация (`main/setup_logic.py`). Суперпользователь: `python manage.py createsuperuser`.

→ **Локальный адрес:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

<a id="config"></a>

## ⚙️ Конфигурация

Переменные читаются в **`reflection/reflection/settings.py`**. Шаблон — **`reflection/.env.prod.example`** → скопируйте в **`reflection/.env`**.

| Переменная | Назначение |
|------------|------------|
| `DJANGO_SECRET_KEY` | Секрет Django |
| `DJANGO_DEBUG` | `1` dev / `0` prod |
| `DJANGO_ALLOWED_HOSTS` | Хосты через запятую |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origin для CSRF (HTTPS) |
| `DJANGO_BEHIND_HTTPS_PROXY` | `1` за nginx с TLS |
| `DJANGO_SQLITE_PATH` | Путь к SQLite (Docker: `/app/db/db.sqlite3`) |
| `REFLECTION_OLLAMA_BASE_URL` | Ollama (локально `127.0.0.1:11434`; в Compose см. `docker-compose.yml`) |
| `REFLECTION_LLM_MODEL` | Имя модели |
| `REFLECTION_LLM_TIMEOUT_S` | Таймаут HTTP к LLM |
| `LE_DOMAIN` | Домен для nginx/Certbot (для `.рф` — Punycode) |
| `LE_EMAIL` | Email для Let’s Encrypt |
| `NGINX_MODE` | `http-only` или `https` |

📎 Подробности по TLS и nginx: **`reflection/deploy/README.md`**

---

<a id="run"></a>

## ▶️ Запуск

```bash
cd diplom-tets/reflection
source .venv/bin/activate
python manage.py runserver
```

При `DJANGO_DEBUG=1` статику отдаёт dev-сервер. Для `DEBUG=0` в проде — `collectstatic` и nginx (см. [Деплой](#deploy)).

---

<a id="accounts"></a>

## 🔑 Учётные записи для тестирования

После автоинициализации БД (если включена):

| Роль | Логин | Пароль |
|------|-------|--------|
| Администратор | `q` | `q` |
| Пользователь | `ivan`, `marina`, `elena`, `dmitry` | `q` |

Только для **dev**. В проде — свои пользователи и секреты.

---

<a id="structure"></a>

## 📁 Структура проекта

```
reflection/
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── deploy/                      # nginx, Let's Encrypt, документация деплоя
├── reflection/                  # settings, urls, wsgi
├── main/
├── users/
├── services/
├── reviews/
├── booking/
├── admin_panel/
├── static/
└── media/
```

Шаблоны лежат в **`templates/`** соответствующих приложений (`INSTALLED_APPS`, `TEMPLATES` в `settings.py`).

---

<a id="admin"></a>

## 🎛️ Админ-панель

Префикс **`/admin-panel/`** (роль администратора).

| Раздел | URL |
|--------|-----|
| Пользователи | `/admin-panel/users/` |
| Статистика | `/admin-panel/stats/` |
| Системные логи | `/admin-panel/logs/` |
| Журнал аудита | `/admin-panel/audit/` |
| Инспектор БД | `/admin-panel/db/` |

**Impersonation:** пользователи → вход от имени → баннер выхода из режима.

```python
# admin_panel/signals.py — идея аудита
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

---

<a id="testing"></a>

## 🧪 Тестирование

```bash
cd diplom-tets/reflection
source .venv/bin/activate

python manage.py test
python manage.py test users
python manage.py check
```

---

<a id="deploy"></a>

## 🚢 Деплой

### Docker Compose (рекомендуется)

```bash
cd diplom-tets/reflection
docker compose up -d --build
```

Сервисы: **`web`**, **`nginx`** (80/443, статика и медиа), **`ollama`**, **`certbot`**. В браузере: **`http://127.0.0.1`** через nginx.

Переменные — **`.env`**. Пошагово (DNS, кириллический домен, HTTPS): **`reflection/deploy/README.md`**.

### Gunicorn + nginx (без Docker)

1. `DEBUG=0`, секреты, `ALLOWED_HOSTS`, при HTTPS — `CSRF_TRUSTED_ORIGINS`, `DJANGO_BEHIND_HTTPS_PROXY`.
2. `collectstatic`; nginx раздаёт `/static/` и `/media/`.
3. `gunicorn reflection.wsgi:application --bind 0.0.0.0:8000`.

`Dockerfile` может использовать `runserver` для демо; для жёсткого prod — заменить на Gunicorn.

---

<a id="license"></a>

## 📜 Лицензия

Распространение на условиях **MIT**. Полный текст лицензии — в файле **[`LICENSE`](LICENSE)** в корне репозитория (рядом с этим README). Краткое описание: [opensource.org/licenses/MIT](https://opensource.org/licenses/MIT).

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT — файл LICENSE"/></a>
</p>

---

<a id="author"></a>

## ✉️ Автор

| | |
|--|--|
| Проект | Дипломная работа, 2026 |
| Организация (контент сайта) | Центр «Отражение», г. Курск, ул. Карла Маркса, 72/20 |
| Телефон | +7 (961) 168-97-98 |

Вопросы по коду — через **Issues** в репозитории.

---

<p align="center">
  <br/>
  <strong>Отражение</strong><br/>
  <sub>Django · SQLite · nginx · Ollama · MIT · 2026</sub>
</p>
