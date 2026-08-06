"""
Главная точка входа для процесса Telegram-бота.

Запускает:
1. Подключение к БД
2. Синхронизацию и запуск активных задач парсинга
3. Periodic re-sync для подхвата изменений из веб-интерфейса
4. Polling Telegram-бота
"""
import asyncio

from src.bot import handlers  # важно: подключаем роутеры до старта polling
from src.bot.dispatcher import bot, dp
from src.db.config import init_db
from src.config import RESYNC_TIMER
from src.services.parser import ParserManager
from src.utils.logger import logger
from tortoise import Tortoise
from src.tg_client.client import ClientPool


async def _periodic_resync(interval: int = RESYNC_TIMER):
    """
    Фоновая задача: периодически перечитывает статусы задач из БД
    и синхронизирует с запущенными задачами ParserManager.

    Это позволяет веб-интерфейсу (запущенному в отдельном процессе)
    изменять статусы задач, и бот подхватит эти изменения.

    Args:
        interval: интервал между проверками в секундах (по умолчанию 30).
    """
    while True:
        await asyncio.sleep(interval)
        try:
            await ParserManager.sync_with_db()
        except Exception as e:
            logger.error(f'Ошибка при ресинхронизации ParserManager: {e}')


async def shutdown():
    # 2a. Остановить все фоновые задачи ParserManager
    for request_id in list(ParserManager._tasks.keys()):
        await ParserManager.stop_request(request_id)

    # 2b. Закрыть все Telegram клиенты
    await ClientPool.close_all()

    # 2c. Закрыть подключение к БД
    await Tortoise.close_connections()

    logger.info('Все ресурсы освобождены')


async def main():
    await init_db()
    await ParserManager.sync_with_db()

    # Запускаем фоновую задачу ресинхронизации
    resync_task = asyncio.create_task(_periodic_resync())
    logger.info('Фоновая ресинхронизация ParserManager запущена ')

    try:
        logger.info('Парсер и бот запущены')
        await dp.start_polling(bot)  # блокирующий запуск бота
    finally:
        logger.info('Завершение работы')
        await shutdown()
        resync_task.cancel()
        try:
            await resync_task
        except asyncio.CancelledError:
            pass



if __name__ == '__main__':
    asyncio.run(main())