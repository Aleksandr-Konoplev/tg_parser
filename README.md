# tg-parser

Парсер для сбора постов из Telegram-каналов.

Позволяет:
- авторизовывать Telegram-аккаунты;
- добавлять каналы для мониторинга;
- настраивать задачи парсинга с фильтрами по ключевым словам;
- собирать посты и отправлять результаты через Telegram-бота;
- просматривать сохранённые посты по задаче с фильтром по дате публикации, постраничной навигацией и возможностью вывести все посты;

## База данных

Проект использует **PostgreSQL** в связке с **Tortoise ORM**.  
Миграции управляются через **Aerich**.

Подключение настраивается через переменную окружения `DB_URL`  
(по умолчанию: `postgres://postgres:password@localhost:5432/name_db`).

### Схема данных


### Описание таблиц

#### `telegram_accounts`

Telegram-аккаунты, с которых выполняется парсинг.

| Колонка | Тип | Ограничения | Описание |
|---|---|---|---|
| id | serial | PK | Первичный ключ |
| phone | varchar(20) | UNIQUE | Номер телефона |
| api_id | int | NOT NULL | api_id из my.telegram.org |
| api_hash | varchar(64) | NOT NULL | api_hash из my.telegram.org |
| session_str | text | nullable | Строка сессии Telethon |
| is_active | bool | NOT NULL, default true | Активен ли аккаунт |
| created_at | timestamptz | NOT NULL, auto_now_add | Время создания записи |

#### `channels`

Каналы, из которых собираются посты.

| Колонка | Тип | Ограничения | Описание |
|---|---|---|---|
| id | serial | PK | Первичный ключ |
| telegram_id | bigint | UNIQUE | Числовой ID канала в Telegram |
| username | varchar(100) | nullable | @username канала |
| title | varchar(255) | NOT NULL | Название канала |
| is_active | bool | NOT NULL, default true | Включён ли канал |

#### `search_requests`

Задачи парсинга.

| Колонка | Тип | Ограничения | Описание |
|---|---|---|---|
| id | serial | PK | Первичный ключ |
| name | varchar(255) | NOT NULL | Название задачи |
| keywords | text | nullable | Ключевые слова через запятую (null — все посты) |
| interval_sec | int | NOT NULL, default 300 | Период между запусками, сек |
| limit_per_run | int | NOT NULL, default 50 | Максимум постов за один запуск |
| status | varchar(20) | NOT NULL, default stopped | Состояние: running / paused / stopped |
| last_run_at | timestamptz | nullable | Время последнего запуска |
| notify_chat_id | bigint | nullable | Чат для отправки результатов |
| created_at | timestamptz | NOT NULL, auto_now_add | Время создания задачи |
| account_id | int | FK → telegram_accounts.id | Аккаунт, с которого парсят |

#### `search_requests_channels`

Связующая таблица many-to-many между задачами и каналами.

| Колонка | Тип | Ограничения | Описание |
|---|---|---|---|
| search_requests_id | int | FK → search_requests.id | ID задачи |
| channel_id | int | FK → channels.id | ID канала |

Уникальность по паре `(search_requests_id, channel_id)`.

#### `posts`

Результаты парсинга.

| Колонка | Тип | Ограничения | Описание |
|---|---|---|---|
| id | serial | PK | Первичный ключ |
| telegram_msg_id | bigint | NOT NULL | ID сообщения в Telegram |
| channel_id | int | FK → channels.id | Канал-источник |
| search_request_id | int | FK → search_requests.id, nullable | Задача, по которой найден пост |
| text | text | nullable | Текст поста |
| media_info | jsonb | nullable | Информация о медиа |
| views | int | nullable | Количество просмотров |
| forwards | int | nullable | Количество репостов |
| replies | int | nullable | Количество комментариев |
| parsed_at | timestamptz | NOT NULL, auto_now_add | Время парсинга |
| posted_at | timestamptz | nullable | Реальная дата публикации поста в Telegram |
| raw_data | jsonb | nullable | Сырые данные Telethon |
| sent_to_chat | bool | NOT NULL, default false | Отправлен ли ботом в notify_chat |

Уникальность по паре `(telegram_msg_id, channel_id)`.

#### `aerich`

Служебная таблица миграций Aerich. Содержит версии применённых миграций.

---

## Деплой (Docker + Docker Compose)

Приложение запускается на сервере в трёх Docker-контейнерах:
- `postgres` — база данных PostgreSQL 16 (данные в volume `pgdata`);
- `bot` — Telegram-бот и парсер (`python src/main.py`);
- `web` — веб-интерфейс FastAPI (`python -m src.web`, порт `WEB_PORT`).

Зависимости внутри образа устанавливаются через Poetry (`Dockerfile`).
Конфигурация читается из файла `.env` (не коммитится).

### Первичная настройка сервера

Установите Docker и Docker Compose v2, добавьте пользователя в группу `docker`
(после этого нужно перелогиниться в SSH):

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Склонируйте репозиторий и создайте `.env` из шаблона:

```bash
cd /opt
git clone https://github.com/Aleksandr-Konoplev/tg_parser.git tg_parser
cd tg_parser

cp .env.example .env
nano .env    # вписать реальные значения (BOT_TOKEN, POSTGRES_PASSWORD, WEB_SECRET_KEY и т.д.)
```

> Для приватного репозитория нужен доступ: Personal Access Token (HTTPS) или SSH-ключ.

### Запуск (первый раз и после изменений)

```bash
cd /opt/tg_parser

# 1. Собрать образы
docker compose build

# 2. Поднять БД и дождаться её готовности
docker compose up -d postgres
docker compose up -d --wait postgres

# 3. Применить миграции Aerich
docker compose run --rm bot aerich upgrade

# 4. Запустить бота и веб-интерфейс
docker compose up -d

# 5. Проверить статус
docker compose ps
```

### Обновление приложения

```bash
cd /opt/tg_parser
git pull
docker compose build
docker compose up -d postgres
docker compose up -d --wait postgres
docker compose run --rm bot aerich upgrade
docker compose up -d
```

### Смена пароля PostgreSQL

Пароль из `POSTGRES_PASSWORD` применяется только при **первой** инициализации
пустого тома `pgdata`. Если позже поменять его в `.env`, это не повлияет на
уже созданную БД. Чтобы сменить пароль:

```bash
# Вариант 1 — сбросить БД полностью (данные будут удалены):
docker compose down -v
docker compose up -d postgres

# Вариант 2 — сменить пароль без потери данных:
docker compose exec postgres psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'новый_пароль';"
# после чего обновите POSTGRES_PASSWORD в .env и пересоздайте bot/web:
docker compose up -d --force-recreate bot web
```

### Полезные команды

```bash
docker compose logs -f bot web      # логи бота и веба
docker compose restart bot          # перезапустить бота
docker compose down                 # остановить (без удаления данных БД)
docker compose down -v              # остановить и удалить данные БД (осторожно!)
```

Веб-интерфейс после запуска доступен по адресу `http://<ip-сервера>:8000`.
