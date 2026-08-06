import asyncio

from src.bot.dispatcher import bot
from src.config import ADMIN_CHAT_ID
from src.utils.logger import logger


# Словарь: account_id → Future. Когда парсеру нужен код от аккаунта,
# он создаёт Future и ждёт, пока бот не разрешит её (вводом кода юзером).
_pending_codes: dict[int, asyncio.Future] = {}
_pending_passwords: dict[int, asyncio.Future] = {}


class AuthManager:

    # Создать запрос кода. Парсер вызовет, бот получит уведомление.
    @staticmethod
    async def request_code(account_id: int) -> str:
        future = asyncio.get_running_loop().create_future()
        _pending_codes[account_id] = future
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"🔐 Требуется код для аккаунта #{account_id}\n"
            f"Отправьте код подтверждения в ответ (5 минут):",
        )
        logger.info(f"Запрошен код для аккаунта {account_id}")
        try:
            return await asyncio.wait_for(future, timeout=300)  # 5 минут
        except asyncio.TimeoutError:
            _pending_codes.pop(account_id, None)
            logger.warning(f"Таймаут ожидания кода для аккаунта {account_id}")
            raise  # пробросить наверх, в ClientPool

    # Бот вызывает этот метод, когда юзер прислал код. Разрешает Future.
    @staticmethod
    async def submit_code(account_id: int, code: str) -> bool:
        future = _pending_codes.pop(account_id, None)
        if not future or future.done():
            return False
        future.set_result(code)
        logger.info(f"Код получен для аккаунта {account_id}")
        return True

    # Запросить 2FA-пароль. Бот покажет промпт, юзер отправит пароль.
    @staticmethod
    async def request_password(account_id: int) -> str:
        future = asyncio.get_running_loop().create_future()
        _pending_passwords[account_id] = future
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"🔑 Для аккаунта #{account_id} включена двухфакторная авторизация.\n"
            f"Отправьте пароль в ответ:",
        )
        try:
            return await asyncio.wait_for(future, timeout=300)
        except asyncio.TimeoutError:
            _pending_passwords.pop(account_id, None)
            logger.warning(f"Таймаут ожидания пароля для аккаунта {account_id}")
            raise

    # Бот вызывает, когда юзер прислал пароль. Разрешает Future.
    @staticmethod
    async def submit_password(account_id: int, password: str) -> bool:
        future = _pending_passwords.pop(account_id, None)
        if not future or future.done():
            return False
        future.set_result(password)
        logger.info(f"Пароль получен для аккаунта {account_id}")
        return True
