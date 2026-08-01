import asyncio

from src.utils.logger import logger

# Словарь: account_id → Future. Когда парсеру нужен код от аккаунта,
# он создаёт Future и ждёт, пока бот не разрешит её (вводом кода юзером).
_pending_codes: dict[int, asyncio.Future] = {}


class AuthManager:

    # Создать запрос кода. Бот получит сигнал показать prompt юзеру.
    @staticmethod
    def request_code(account_id: int) -> asyncio.Future:
        future = asyncio.get_running_loop().create_future()
        _pending_codes[account_id] = future
        logger.info(f"Запрошен код для аккаунта {account_id}")
        return future

    # Бот вызывает этот метод, когда юзер прислал код. Разрешает Future.
    @staticmethod
    async def submit_code(account_id: int, code: str) -> bool:
        future = _pending_codes.pop(account_id, None)
        if not future:
            return False  # код не запрашивали
        if future.done():
            return False
        future.set_result(code)
        return True