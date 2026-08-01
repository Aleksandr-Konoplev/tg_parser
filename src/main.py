import asyncio

from src.db.config import init_db
from src.services.parser import ParserManager
from src.utils.logger import logger


async def main():
    await init_db()
    await ParserManager.sync_with_db()  # поднимаем фоновые циклы для running-задач
    logger.info("Парсер запущен")
    # TODO (Шаг 6): запуск Telegram бота. Пока держим процесс живым
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())