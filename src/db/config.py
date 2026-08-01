from tortoise import Tortoise
from src.config import DB_URL


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