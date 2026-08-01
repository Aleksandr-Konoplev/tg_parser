import asyncio
from src.tg_client.auth import AuthManager
from telethon import TelegramClient
from telethon.sessions import StringSession

from src.db.models import TelegramAccount
from src.utils.logger import logger


_client_pool: dict[int, TelegramClient] = {}


class ClientPool:

    # Получить клиент для аккаунта. Создаёт и авторизует, если ещё нет.
    @staticmethod
    async def get_client(account: TelegramAccount) -> TelegramClient:
        # Уже создавали — возвращаем как есть
        if account.id in _client_pool:
            return _client_pool[account.id]

        # Создаём новый клиент Telethon
        # StringSession — хранит сессию как строку (мы кладём её в БД),
        # чтобы не таскать .session файлы и авторизовываться заново.
        client = TelegramClient(
            StringSession(account.session_str),
            account.api_id,
            account.api_hash,
        )

        # Подключаемся к серверу Telegram
        await client.connect()

        if not await client.is_user_authorized():
            logger.warning(f"Аккаунт {account.phone} не авторизован, ждём код...")
            # request_code вернёт Future, который бот разрешит вводом кода
            code = await AuthManager.request_code(account.id)
            # client.start подставит номер и код автоматически
            await client.start(
                phone=lambda: account.phone,
                code_callback=lambda: code,
            )
            # сессия авторизована — сохраняем в БД для следующих запусков
            await ClientPool.save_session(account, client)
        else:
            logger.info(f"Аккаунт {account.phone} авторизован из сохранённой сессии")

    # Сохранить строку сессии обратно в БД (после успешной авторизации)
    @staticmethod
    async def save_session(account: TelegramAccount, client: TelegramClient):
        account.session_str = client.session.save()
        await account.save(update_fields=["session_str"])
        logger.info(f"Сессия аккаунта {account.phone} сохранена")

    # Получить посты из канала
    # offset_id — с какого сообщения парсить (не включая его)
    # Используем, чтобы забирать только НОВЫЕ посты после last_run
    @staticmethod
    async def get_messages(account: TelegramAccount, channel_ref, limit: int = 50, offset_id: int | None = None):
        client = await ClientPool.get_client(account)

        # channel_ref — это username ("@channel") или числовой ID
        # Telethon умеет оба варианта. Если передали число — используем напрямую,
        # если строку — сначала резолвим entity.
        entity = channel_ref
        if isinstance(channel_ref, str):
            entity = await client.get_entity(channel_ref)

        kwargs = {"limit": limit}
        if offset_id:
            kwargs["offset_id"] = offset_id  # пропустить уже распарсенные

        # get_messages возвращает список сообщений от новых к старым
        messages = await client.get_messages(entity, **kwargs)
        return messages

    # Закрыть все клиенты (вызываем при остановке приложения)
    @staticmethod
    async def close_all():
        for client in _client_pool.values():
            await client.disconnect()
        _client_pool.clear()
        logger.info("Все Telegram-клиенты закрыты")