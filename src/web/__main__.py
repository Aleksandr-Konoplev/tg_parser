"""
Точка входа для запуска веб-интерфейса как отдельного процесса.

Запуск: python -m src.web

Работает независимо от бота. Инициализирует:
- Подключение к БД (Tortoise ORM)
- FastAPI приложение
- Uvicorn сервер
"""
import asyncio
import sys

import uvicorn
from loguru import logger

from src.config import WEB_HOST, WEB_PORT, LOG_LEVEL, ADMIN_CHAT_ID
from src.db.config import init_db
from src.db.models import WebUser


async def ensure_admin_user():
    """
    Создаёт WebUser для администратора (ADMIN_CHAT_ID) при первом запуске.
    Админ с is_admin=True видит все данные, включая те, что без владельца (user_id IS NULL).
    """
    if not ADMIN_CHAT_ID:
        logger.warning("ADMIN_CHAT_ID не задан — администратор веба не создан")
        return

    user, created = await WebUser.get_or_create(
        telegram_id=ADMIN_CHAT_ID,
        defaults={
            "is_admin": True,
            "username": "admin",
        },
    )
    if created:
        logger.info(f"Создан администратор веба (telegram_id={ADMIN_CHAT_ID})")
    elif not user.is_admin:
        # Если пользователь уже существует, но не админ — делаем админом
        user.is_admin = True
        await user.save()
        logger.info(f"Пользователь {ADMIN_CHAT_ID} повышен до администратора")


async def main():
    """Основная функция запуска веб-сервера."""
    logger.remove()
    logger.add(sys.stderr, level=LOG_LEVEL)

    logger.info("Запуск веб-интерфейса tg-parser...")

    # Инициализируем БД
    await init_db()
    logger.info("База данных подключена")

    # Создаём пользователя-администратора
    await ensure_admin_user()

    # Импортируем FastAPI приложение
    # (импорт после init_db, так как при импорте создаются Jinja2 ссылки на routes)
    from src.web.server import app

    # Запускаем uvicorn
    logger.info(f"Сервер запущен на http://{WEB_HOST}:{WEB_PORT}")
    config = uvicorn.Config(
        app=app,
        host=WEB_HOST,
        port=WEB_PORT,
        log_level=LOG_LEVEL.lower(),
        # Не перезагружать при изменении кода — это отдельный процесс
        reload=False,
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())