from tortoise import Tortoise
from src.config import DB_URL

# Конфигурация Tortoise ORM.
# "connections" — подключения к БД (у нас одно, default)
# "apps" — приложения моделей. "models" — список модулей с моделями.
#   "aerich.models" обязателен — это служебная таблица для миграций.
TORTOISE_ORM = {
    "connections": {"default": DB_URL},
    "apps": {
        "models": {
            "models": ["src.db.models", "aerich.models"],
            "default_connection": "default",
        }
    },
}


# Инициализация Tortoise: подключается к БД и читает модели
async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)