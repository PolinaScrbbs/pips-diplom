# Деплой: Nginx, домен, Let’s Encrypt

## 1. Параметры домена и Let’s Encrypt

Перед выпуском сертификата задайте в `.env` (или скопируйте из `.env.prod.example`):

| Переменная     | Назначение |
|----------------|------------|
| `LE_DOMAIN`    | Полное имя хоста (например `app.example.com`), по нему DNS должен указывать на ваш публичный IP. |
| `LE_EMAIL`     | Email для аккаунта Let’s Encrypt (уведомления об истечении, политика). |

Убедитесь, что **A/AAAA** записи домена указывают на IP машины (или роутера с пробросом портов).

## 2. Проверка портов 80 и 443 на macOS

На Mac порты **80** и **443** должны быть свободны для Docker (не заняты Apache, «AirPlay Receiver» и т.п.).

Проверка, кто слушает порты:

```bash
lsof -nP -iTCP:80 -sTCP:LISTEN
lsof -nP -iTCP:443 -sTCP:LISTEN
```

Если вывод пустой — обычно можно биндить nginx. Если есть процесс — остановите его или смените сервис.

Проверка с локальной машины (после запуска nginx в Docker):

```bash
curl -I --connect-timeout 3 "http://127.0.0.1"
curl -I --connect-timeout 3 "https://127.0.0.1" -k
```

Снаружи (с другого хоста) после проброса на роутере:

```bash
curl -I "http://LE_DOMAIN"
```

## 3. Проброс портов на роутере

На роутере настройте **DNAT**: внешний **TCP 80 → 80** и **TCP 443 → 443** на локальный IP вашего Mac (статический DHCP или резервация по MAC).

Let’s Encrypt по HTTP-01 должен достучаться до **вашего** `http://LE_DOMAIN/.well-known/acme-challenge/...` из интернета.

## 4. Режимы Nginx (`NGINX_MODE`)

| Значение      | Когда использовать |
|---------------|---------------------|
| `http-only`   | Первый запуск: только HTTP:80, webroot для ACME и прокси на `web:8000`. HTTPS не настраивается (сертификатов ещё нет). |
| `https`       | После успешного `certbot certonly`: редирект HTTP→HTTPS и TLS на :443. |

Переключение: в `.env` выставить `NGINX_MODE=https`, затем `docker compose up -d nginx`.

Подробные шаги первичного выпуска сертификата — в разделе «Первичный выпуск сертификата» в конце этого файла.

## 5. Переменные Django за HTTPS-прокси

См. `.env.prod.example`: `DJANGO_BEHIND_HTTPS_PROXY=1`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_ALLOWED_HOSTS` с вашим доменом.

## 6. Обновление сертификатов

Сервис `certbot` в фоне периодически выполняет `certbot renew`. После фактического обновления файлов на диске nginx нужно перечитать сертификат:

```bash
docker compose exec nginx nginx -s reload
```

Либо перезапуск контейнера nginx: `docker compose restart nginx`. Раз в несколько дней/неделю этого достаточно для дипломной среды.

## 7. Первичный выпуск сертификата и финальный запуск

Ниже предполагается, что в `.env` заданы **`LE_DOMAIN`**, **`LE_EMAIL`**, для Django — **`DJANGO_ALLOWED_HOSTS`** (тот же хост), **`DJANGO_CSRF_TRUSTED_ORIGINS=https://<хост>`**, при необходимости **`DJANGO_BEHIND_HTTPS_PROXY=1`**. До выпуска сертификата держите **`NGINX_MODE=http-only`**.

### 7.1 Запуск стека (HTTP, без TLS)

Из каталога проекта (`reflection`, где лежит `docker-compose.yml`):

```bash
docker compose up -d --build
```

Проверьте, что сайт открывается по HTTP снаружи (через домен):

```bash
curl -I "http://${LE_DOMAIN}"
```

Должен отвечать nginx → Django (например `200`, `302`, `404` — главное, что не таймаут).

### 7.2 Выпуск сертификата (webroot)

Когда порт **80** доступен из интернета и DNS указывает на вашу машину:

```bash
docker compose run --rm --entrypoint certbot certbot certonly \
  --webroot \
  -w /var/www/certbot \
  -d "${LE_DOMAIN}" \
  --email "${LE_EMAIL}" \
  --agree-tos \
  --non-interactive
```

При успехе файлы появятся в volume `letsencrypt` (пути вида `/etc/letsencrypt/live/<LE_DOMAIN>/` внутри контейнеров).

### 7.3 Включение HTTPS в Nginx

В `.env` установите:

```bash
NGINX_MODE=https
```

Пересоздайте nginx (конфиг подставляется при старте):

```bash
docker compose up -d nginx
```

Проверка редиректа и HTTPS:

```bash
curl -I "http://${LE_DOMAIN}"
curl -I "https://${LE_DOMAIN}"
```

При обновлении сертификатов фоновым `certbot renew` выполните перезагрузку конфигурации nginx (см. раздел 6).

### 7.4 Локальная разработка без домена

Без публичного DNS и Let’s Encrypt оставьте **`NGINX_MODE=http-only`** и при необходимости **`LE_DOMAIN=localhost`**. Прямой доступ к приложению: **`http://127.0.0.1`** (порт **80** на хосте проксирует в `web:8000`). Выпуск настоящего сертификата для `localhost` у Let’s Encrypt недоступен.
