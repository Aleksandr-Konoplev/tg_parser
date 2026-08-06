from tortoise import fields, models


class WebUser(models.Model):
    """
    Пользователь веб-интерфейса, привязанный к Telegram-аккаунту.
    Каждый пользователь видит только свои данные.
    Пользователь с is_admin=True (старый ADMIN_CHAT_ID) видит также данные без владельца.
    """
    id = fields.IntField(pk=True)
    telegram_id = fields.BigIntField(unique=True)  # Числовой ID пользователя в Telegram
    username = fields.CharField(max_length=100, null=True)  # @username
    chat_id = fields.BigIntField(null=True)  # Для отправки кодов через Bot API
    is_admin = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "web_users"

    def __str__(self):
        return self.username or str(self.telegram_id)


class AuthCode(models.Model):
    """
    Одноразовый код для входа в веб-интерфейс.
    Генерируется при POST /login, отправляется в Telegram пользователю,
    проверяется при POST /verify.
    """
    id = fields.IntField(pk=True)
    telegram_id = fields.BigIntField()  # Кому отправлен код
    code = fields.CharField(max_length=6)  # 6 цифр
    expires_at = fields.DatetimeField()  # Код действует 5 минут
    is_used = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "auth_codes"

    def __str__(self):
        return f"Code {self.code} for {self.telegram_id}"


class TelegramAccount(models.Model):
    """
    Аккаунт Telegram, с которого парсим каналы.
    Привязан к пользователю веба через user_id (null = старый админ).
    """
    id = fields.IntField(pk=True)
    phone = fields.CharField(max_length=20, unique=True)
    api_id = fields.IntField()
    api_hash = fields.CharField(max_length=128)
    session_str = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    user = fields.ForeignKeyField("models.WebUser", related_name="telegram_accounts", null=True)

    class Meta:
        table = "telegram_accounts"

    def __str__(self):
        return self.phone


class Channel(models.Model):
    """
    Канал Telegram для парсинга.
    Привязан к пользователю веба через user_id (null = старый админ).
    """
    id = fields.IntField(pk=True)
    telegram_id = fields.BigIntField(unique=True)
    username = fields.CharField(max_length=100, null=True)
    title = fields.CharField(max_length=255)
    is_active = fields.BooleanField(default=True)
    user = fields.ForeignKeyField("models.WebUser", related_name="channels", null=True)

    class Meta:
        table = "channels"

    def __str__(self):
        return self.username or self.title


class SearchRequest(models.Model):
    """
    Задача парсинга: какие каналы, с какого аккаунта, с какой периодичностью.
    Привязана к пользователю веба через user_id (null = старый админ).
    """
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    account = fields.ForeignKeyField("models.TelegramAccount", related_name="search_requests")
    channels = fields.ManyToManyField("models.Channel", related_name="search_requests")
    keywords = fields.TextField(null=True)
    interval_sec = fields.IntField(default=300)
    limit_per_run = fields.IntField(default=50)
    status = fields.CharField(max_length=20, default="stopped")
    last_run_at = fields.DatetimeField(null=True)
    notify_chat_id = fields.BigIntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    user = fields.ForeignKeyField("models.WebUser", related_name="search_requests", null=True)

    class Meta:
        table = "search_requests"

    def __str__(self):
        return self.name


class Post(models.Model):
    """
    Пост — результат парсинга.
    Не привязан напрямую к пользователю — связь через SearchRequest или Channel.
    """
    id = fields.IntField(pk=True)
    telegram_msg_id = fields.BigIntField()
    channel = fields.ForeignKeyField("models.Channel", related_name="posts")
    search_request = fields.ForeignKeyField("models.SearchRequest", related_name="posts", null=True)
    text = fields.TextField(null=True)
    media_info = fields.JSONField(null=True)
    views = fields.IntField(null=True)
    forwards = fields.IntField(null=True)
    replies = fields.IntField(null=True)
    parsed_at = fields.DatetimeField(auto_now_add=True)
    posted_at = fields.DatetimeField(null=True)
    raw_data = fields.JSONField(null=True)
    sent_to_chat = fields.BooleanField(default=False)

    class Meta:
        table = "posts"
        unique_together = (("telegram_msg_id", "channel"))

    def __str__(self):
        return f"Post #{self.telegram_msg_id}"