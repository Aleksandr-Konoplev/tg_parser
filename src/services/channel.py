"""
Сервис для работы с Channel.
Поддерживает изоляцию по user_id: каждый пользователь веба видит только свои каналы.
Если user_id=None (вызов из бота), то не фильтрует по владельцу.
"""
from src.db.models import Channel, WebUser
from src.utils.logger import logger
from tortoise.expressions import Q


class ChannelService:

    @staticmethod
    async def create(telegram_id: int, username: str | None, title: str, user_id: int | None = None):
        """
        Создать канал для парсинга.
        Если канал с таким telegram_id уже существует (в т.ч. неактивный) —
        реактивирует его и обновляет данные.
        Если user_id передан — привязывает канал к пользователю веба.
        Если user_id=None — канал считается общим (старый админ).
        """
        existing = await Channel.get_or_none(telegram_id=telegram_id)
        if existing:
            existing.username = username
            existing.title = title
            existing.is_active = True
            if user_id is not None:
                user = await WebUser.get_or_none(id=user_id)
                if user:
                    existing.user = user
            await existing.save()
            logger.info(f"Канал восстановлен: {username or telegram_id}")
            return existing

        kwargs = {
            "telegram_id": telegram_id,
            "username": username,
            "title": title,
        }
        if user_id is not None:
            user = await WebUser.get_or_none(id=user_id)
            if user:
                kwargs["user"] = user
        channel = await Channel.create(**kwargs)
        logger.info(f"Канал создан: {username or telegram_id}")
        return channel

    @staticmethod
    async def get(channel_id: int):
        """Достать канал по ID."""
        return await Channel.get_or_none(id=channel_id)

    @staticmethod
    async def get_by_telegram_id(telegram_id: int):
        """Достать канал по telegram_id."""
        return await Channel.get_or_none(telegram_id=telegram_id)

    @staticmethod
    async def get_active(user_id: int | None = None, include_common: bool = False):
        """
        Получить активные каналы.
        Если include_common=True — свои + общие.
        """
        if user_id is None:
            return await Channel.filter(is_active=True).order_by("id")
        query = Q(user_id=user_id)
        if include_common:
            query |= Q(user_id__isnull=True)
        return await Channel.filter(Q(is_active=True) & query).order_by("id")

    @staticmethod
    async def get_all(user_id: int | None = None, include_common: bool = False):
        """
        Получить все каналы.
        Если include_common=True — свои + общие.
        """
        if user_id is None:
            return await Channel.all().order_by("id")
        query = Q(user_id=user_id)
        if include_common:
            query |= Q(user_id__isnull=True)
        return await Channel.filter(query).order_by("id")

    @staticmethod
    async def update(channel_id: int, **fields):
        """Обновить поля канала."""
        channel = await ChannelService.get(channel_id)
        if not channel:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(channel, key, value)
        await channel.save()
        return channel

    @staticmethod
    async def delete(channel_id: int):
        """Мягкое удаление канала (is_active=False)."""
        channel = await ChannelService.get(channel_id)
        if not channel:
            return False
        channel.is_active = False
        await channel.save(update_fields=["is_active"])
        logger.info(f"Канал {channel_id} отключён (soft delete)")
        return True
