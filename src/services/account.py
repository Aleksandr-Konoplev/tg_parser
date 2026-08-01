from src.db.models import TelegramAccount
from src.utils.logger import logger


# Класс-сервис: инкапсулирует все операции с аккаунтами.
# Методы статические — вызываются без создания экземпляра:
#   AccountService.create(...) вместо service = AccountService(); service.create(...)
class AccountService:

    # Создание аккаунта. Вернёт (аккаунт, ошибка).
    # Кортеж — чтобы бот мог сразу показать ошибку, не ловя исключения.
    @staticmethod
    async def create(phone: str, api_id: int, api_hash: str):
        try:
            account = await TelegramAccount.create(
                phone=phone,
                api_id=api_id,
                api_hash=api_hash,
            )
            logger.info(f"Аккаунт создан: {phone}")
            return account, None
        except Exception as e:
            # Сюда попадает и IntegrityError (phone уже есть) и любые другие
            logger.error(f"Ошибка создания аккаунта {phone}: {e}")
            return None, str(e)

    # Достать один аккаунт по id. Вернёт None если нет
    @staticmethod
    async def get(account_id: int):
        return await TelegramAccount.get_or_none(id=account_id)

    # Все аккаунты prefetch — для related_name (не используется, но удобно держать шаблон)
    @staticmethod
    async def get_all():
        return await TelegramAccount.all().order_by("id")

    # Обновить поля аккаунта (только переданные не-None)
    @staticmethod
    async def update(account_id: int, **fields):
        account = await AccountService.get(account_id)
        if not account:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(account, key, value)
        await account.save()
        logger.info(f"Аккаунт {account_id} обновлён")
        return account

    # Включить/выключить аккаунт (не удаляем — чтобы не терять сессии)
    @staticmethod
    async def set_active(account_id: int, is_active: bool):
        account = await AccountService.get(account_id)
        if not account:
            return None
        account.is_active = is_active
        await account.save()
        return account

    # Полное удаление аккаунта. ВАЖНО: удалит и связанные SearchRequest (ON DELETE CASCADE)
    @staticmethod
    async def delete(account_id: int):
        account = await AccountService.get(account_id)
        if not account:
            return False
        await account.delete()
        logger.info(f"Аккаунт {account_id} удалён")
        return True