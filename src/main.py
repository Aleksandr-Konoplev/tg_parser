import asyncio

from src.bot import handlers  # важно: подключаем роутеры до старта polling
from src.bot.dispatcher import bot, dp
from src.db.config import init_db
from src.services.parser import ParserManager
from src.utils.logger import logger


async def main():
    await init_db()
    await ParserManager.sync_with_db()
    logger.info("Парсер и бот запущены")
    await dp.start_polling(bot)  # блокирующий запуск бота


if __name__ == "__main__":
    asyncio.run(main())