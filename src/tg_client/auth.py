import asyncio

from src.bot.dispatcher import bot
from src.config import ADMIN_CHAT_ID
from src.utils.logger import logger


# Словарь: account_id → Future. Когда парсеру нужен код от аккаунта,
# он создаёт Future и ждёт, пока бот не разрешит её (вводом кода юзером).
_pending_codes: dict[int, asyncio.Future] = {}


class AuthManager:

    # Создать запрос кода. Парсер вызовет, бот получит уведомление.
    @staticmethod
    async def request_code(account_id: int) -> str:
        future = asyncio.get_running_loop().create_future()
        _pending_codes[account_id] = future
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"🔐 Требуется код для аккаунта #{account_id}\n"
            f"Отправьте код подтверждения в ответ:",
        )
        logger.info(f"Запрошен код для аккаунта {account_id}")
        return await future  # ждём код от пользователя

    # Бот вызывает этот метод, когда юзер прислал код. Разрешает Future.
    @staticmethod
    async def submit_code(account_id: int, code: str) -> bool:
        future = _pending_codes.pop(account_id, None)
        if not future or future.done():
            return False
        future.set_result(code)
        logger.info(f"Код получен для аккаунта {account_id}")
        return True