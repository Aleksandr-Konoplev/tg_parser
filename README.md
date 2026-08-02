# tg-parser

Парсер для сбора постов из Telegram-каналов.

Позволяет:
- авторизовывать Telegram-аккаунты;
- добавлять каналы для мониторинга;
- настраивать задачи парсинга с фильтрами по ключевым словам;
- собирать посты и отправлять результаты через Telegram-бота.

## База данных

Проект использует **PostgreSQL** в связке с **Tortoise ORM**.  
Миграции управляются через **Aerich**.

Подключение настраивается через переменную окружения `DB_URL`  
(по умолчанию: `postgres://postgres:postgres@localhost:5432/tg_parser`).

### Схема данных

```mermaid
erDiagram
    telegram_accounts ||--o{ search_requests : "account_id"
    search_requests ||--o{ search_requests_channels : ""
    channels ||--o{ search_requests_channels : ""
    search_requests ||--o{ posts : "search_request_id"
    channels ||--o{ posts : "channel_id"

    telegram_accounts {
        serial id PK
        varchar phone
        int api_id
        varchar api_hash
        text session_str
        bool is_active
        timestamptz created_at
    }

    channels {
        serial id PK
        bigint telegram_id
        varchar username
        varchar title
        bool is_active
    }

    search_requests {
        serial id PK
        varchar name
        text keywords
        int interval_sec
        int limit_per_run
        varchar status
        timestamptz last_run_at
        bigint notify_chat_id
        timestamptz created_at
        int account_id FK
    }

    search_requests_channels {
        int search_requests_id FK
        int channel_id FK
    }

    posts {
        serial id PK
        bigint telegram_msg_id
        int channel_id FK
        int search_request_id FK
        text message_text
        jsonb media_info
        int views
        int forwards
        int replies
        timestamptz parsed_at
        jsonb raw_data
        bool sent_to_chat
    }
```

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
| raw_data | jsonb | nullable | Сырые данные Telethon |
| sent_to_chat | bool | NOT NULL, default false | Отправлен ли ботом в notify_chat |

Уникальность по паре `(telegram_msg_id, channel_id)`.

#### `aerich`

Служебная таблица миграций Aerich. Содержит версии применённых миграций.
