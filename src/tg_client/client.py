from src.tg_client.auth import AuthManager
from telethon.errors import SessionPasswordNeededError
from telethon import TelegramClient
from telethon.sessions import StringSession

from src.db.models import TelegramAccount
from src.utils.logger import logger
import asyncio
from src.bot.dispatcher import bot
from src.config import ADMIN_CHAT_ID


_client_pool: dict[int, TelegramClient] = {}


class ClientPool:

    # Получить клиент для аккаунта. Создаёт и авторизует, если ещё нет.
    @staticmethod
    async def get_client(account: TelegramAccount) -> TelegramClient | None:
        if account.id in _client_pool:
            return _client_pool[account.id]

        client = TelegramClient(
            StringSession(account.session_str),
            account.api_id,
            account.api_hash,
        )
        await client.connect()

        if not await client.is_user_authorized():
            logger.warning(f"Аккаунт {account.phone} не авторизован, запрашиваем код...")
            await client.send_code_request(account.phone)

            # Шаг 1: запрашиваем код с таймаутом 5 минут
            try:
                code = await AuthManager.request_code(account.id)
            except asyncio.TimeoutError:
                logger.error(f"Таймаут ожидания кода для аккаунта {account.phone}")
                await client.disconnect()
                await bot.send_message(
                    ADMIN_CHAT_ID,
                    f"⏱ Таймаут авторизации аккаунта {account.phone} — код не получен за 5 минут",
                )
                return None
            except Exception as e:
                logger.error(f"Ошибка запроса кода для {account.phone}: {e}")
                await client.disconnect()
                return None

            # Шаг 2: входим с кодом
            try:
                await client.sign_in(account.phone, code)
            except SessionPasswordNeededError:
                logger.warning(f"Аккаунт {account.phone}: требуется 2FA-пароль")
                try:
                    password = await AuthManager.request_password(account.id)
                    await client.sign_in(password=password)
                except asyncio.TimeoutError:
                    logger.error(f"Таймаут ожидания пароля для аккаунта {account.phone}")
                    await client.disconnect()
                    await bot.send_message(
                        ADMIN_CHAT_ID,
                        f"⏱ Таймаут 2FA-пароля для аккаунта {account.phone}",
                    )
                    return None
                except Exception as e:
                    logger.error(f"Ошибка запроса пароля: {e}")
                    await client.disconnect()
                    return None

            await ClientPool.save_session(account, client)
        else:
            logger.info(f"Аккаунт {account.phone} авторизован из сохранённой сессии")

        _client_pool[account.id] = client
        return client

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
        if client is None:
            return []

        entity = channel_ref
        if isinstance(channel_ref, str):
            entity = await client.get_entity(channel_ref)

        kwargs = {"limit": limit}
        if offset_id:
            kwargs["offset_id"] = offset_id  # пропустить уже распарсенные

        # get_messages возвращает список сообщений от новых к старым
        messages = await client.get_messages(entity, **kwargs)
        return messages

    @staticmethod
    async def remove_client(account_id: int):
        """Закрыть и удалить клиент из пула (например, при отключении аккаунта)."""
        client = _client_pool.pop(account_id, None)
        if client:
            await client.disconnect()
            logger.info(f"Клиент аккаунта {account_id} закрыт")

    # Закрыть все клиенты (вызываем при остановке приложения)
    @staticmethod
    async def close_all():
        for client in _client_pool.values():
            await client.disconnect()
        _client_pool.clear()
        logger.info("Все Telegram-клиенты закрыты")