"""
Сервис для работы с TelegramAccount.
Поддерживает изоляцию по user_id: каждый пользователь веба видит только свои аккаунты.
Если user_id=None (вызов из бота), то не фильтрует по владельцу.
"""
from src.db.models import TelegramAccount, WebUser
from src.utils.logger import logger
from tortoise.expressions import Q


class AccountService:

    @staticmethod
    async def create(phone: str, api_id: int, api_hash: str, user_id: int | None = None):
        """
        Создать аккаунт для парсинга.
        Если user_id передан — привязывает аккаунт к конкретному пользователю веба.
        Если user_id=None — аккаунт считается общим (старый админ).
        """
        try:
            kwargs = {
                "phone": phone,
                "api_id": api_id,
                "api_hash": api_hash,
            }
            if user_id is not None:
                user = await WebUser.get_or_none(id=user_id)
                if user:
                    kwargs["user"] = user
            account = await TelegramAccount.create(**kwargs)
            logger.info(f"Аккаунт создан: {phone}")
            return account, None
        except Exception as e:
            logger.error(f"Ошибка создания аккаунта {phone}: {e}")
            return None, str(e)

    @staticmethod
    async def get(account_id: int):
        """Достать аккаунт по ID. Возвращает None если нет."""
        return await TelegramAccount.get_or_none(id=account_id)

    @staticmethod
    async def get_all(user_id: int | None = None, include_common: bool = False):
        """
        Все аккаунты, доступные пользователю.
        Если user_id=None — все аккаунты.
        Если include_common=True — свои + общие (user_id=None).
        """
        if user_id is None:
            return await TelegramAccount.all().order_by("id")
        query = Q(user_id=user_id)
        if include_common:
            query |= Q(user_id__isnull=True)
        return await TelegramAccount.filter(query).order_by("id")

    @staticmethod
    async def update(account_id: int, **fields):
        """Обновить поля аккаунта (только переданные не-None)."""
        account = await AccountService.get(account_id)
        if not account:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(account, key, value)
        await account.save()
        logger.info(f"Аккаунт {account_id} обновлён")
        return account

    @staticmethod
    async def set_active(account_id: int, is_active: bool):
        """Включить/выключить аккаунт (не удаляем — сохраняем сессии).
           При отключении закрывает Telegram-клиент, если он был создан."""
        account = await AccountService.get(account_id)
        if not account:
            return None
        account.is_active = is_active
        await account.save()
        if not is_active:
            from src.tg_client.client import ClientPool
            await ClientPool.remove_client(account_id)
        logger.info(f"Аккаунт {account_id} {'активирован' if is_active else 'отключён'}")
        return account

    @staticmethod
    async def delete(account_id: int):
        """Мягкое удаление: отключает аккаунт (is_active=False), сохраняя данные."""
        account = await AccountService.get(account_id)
        if not account:
            return False
        account.is_active = False
        await account.save(update_fields=["is_active"])
        logger.info(f"Аккаунт {account_id} отключён (soft delete)")
        return True
