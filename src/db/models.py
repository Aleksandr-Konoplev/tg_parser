from tortoise import fields, models


# Аккаунт Telegram, с которого парсим каналы
class TelegramAccount(models.Model):
    id = fields.IntField(pk=True)  # первичный ключ (serial)
    phone = fields.CharField(max_length=20, unique=True)  # номер +7999...
    api_id = fields.IntField()  # из my.telegram.org
    api_hash = fields.CharField(max_length=64)  # из my.telegram.org
    session_str = fields.TextField(null=True)  # сессия Telethon (строка) для переавторизации без SMS
    is_active = fields.BooleanField(default=True)  # включён/отключён
    created_at = fields.DatetimeField(auto_now_add=True)  # время создания

    class Meta:
        table = "telegram_accounts"  # имя таблицы в БД

    def __str__(self):
        return self.phone


# Канал, который парсим
class Channel(models.Model):
    id = fields.IntField(pk=True)
    telegram_id = fields.BigIntField(unique=True)  # числовой ID канала в TG
    username = fields.CharField(max_length=100, null=True)  # @username (может отсутствовать)
    title = fields.CharField(max_length=255)  # название канала
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "channels"

    def __str__(self):
        return self.username or self.title


# Задача парсинга: какие каналы, с каким аккаунтом, как часто, фильтры
class SearchRequest(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)  # название задачи, например "Крипта"
    account = fields.ForeignKeyField("models.TelegramAccount", related_name="search_requests")  # с какого аккаунта парсим
    channels = fields.ManyToManyField("models.Channel", related_name="search_requests")  # какие каналы
    keywords = fields.TextField(null=True)  # фильтр слов через запятую (null = все посты)
    interval_sec = fields.IntField(default=300)  # период между запусками, сек
    limit_per_run = fields.IntField(default=50)  # максимум постов за один запуск
    status = fields.CharField(max_length=20, default="stopped")  # running / paused / stopped
    last_run_at = fields.DatetimeField(null=True)  # последний запуск
    notify_chat_id = fields.BigIntField(null=True)  # чат, куда бот шлёт результаты
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "search_requests"

    def __str__(self):
        return self.name


# Пост — результат парсинга
class Post(models.Model):
    id = fields.IntField(pk=True)
    telegram_msg_id = fields.BigIntField()  # ID сообщения в Telegram
    channel = fields.ForeignKeyField("models.Channel", related_name="posts")  # из какого канала
    search_request = fields.ForeignKeyField("models.SearchRequest", related_name="posts", null=True)  # по какой задаче найден
    text = fields.TextField(null=True)  # текст поста
    media_info = fields.JSONField(null=True)  # тип медиа и ссылки (JSON)
    views = fields.IntField(null=True)  # просмотры
    forwards = fields.IntField(null=True)  # репосты
    replies = fields.IntField(null=True)  # комментарии
    parsed_at = fields.DatetimeField(auto_now_add=True)  # когда распарсен
    posted_at = fields.DatetimeField(null=True)  # реальная дата публикации в Telegram
    raw_data = fields.JSONField(null=True)  # сырые данные Telethon для отладки
    sent_to_chat = fields.BooleanField(default=False)  # отправлен ли ботом в notify_chat

    class Meta:
        table = "posts"
        unique_together = (("telegram_msg_id", "channel"))  # не дублировать один пост

    def __str__(self):
        return f"Post #{self.telegram_msg_id}"