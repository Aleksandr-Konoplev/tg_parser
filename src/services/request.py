"""
Сервис для работы с SearchRequest (задачами парсинга).
Поддерживает изоляцию по user_id: каждый пользователь веба видит только свои задачи.
Если user_id=None (вызов из бота), то не фильтрует по владельцу.
"""
from src.db.models import SearchRequest, Channel, WebUser
from src.utils.logger import logger
from tortoise.expressions import Q


class RequestService:

    @staticmethod
    async def create(name: str, account_id: int, keywords: str | None = None,
                     interval_sec: int = 300, limit_per_run: int = 50,
                     notify_chat_id: int | None = None, user_id: int | None = None):
        """
        Создать задачу парсинга.
        Если user_id передан — привязывает задачу к пользователю веба.
        """
        kwargs = {
            "name": name,
            "account_id": account_id,
            "keywords": keywords,
            "interval_sec": interval_sec,
            "limit_per_run": limit_per_run,
            "notify_chat_id": notify_chat_id,
        }
        if user_id is not None:
            user = await WebUser.get_or_none(id=user_id)
            if user:
                kwargs["user"] = user
        request = await SearchRequest.create(**kwargs)
        return request

    @staticmethod
    async def get(request_id: int):
        """Достать задачу по ID."""
        return await SearchRequest.get_or_none(id=request_id)

    @staticmethod
    async def get_all(user_id: int | None = None, include_common: bool = False):
        """
        Получить все задачи.
        Если include_common=True — свои + общие.
        """
        if user_id is None:
            return await SearchRequest.all().order_by("-id")
        query = Q(user_id=user_id)
        if include_common:
            query |= Q(user_id__isnull=True)
        return await SearchRequest.filter(query).order_by("-id")

    @staticmethod
    async def get_running():
        """Активные задачи — их обрабатывает планировщик парсера."""
        return await SearchRequest.filter(status="running")

    @staticmethod
    async def add_channel(request_id: int, channel_id: int):
        """Привязать канал к задаче."""
        request = await SearchRequest.get_or_none(id=request_id)
        if not request:
            return None
        channel = await Channel.get_or_none(id=channel_id)
        if not channel:
            return None
        await request.channels.add(channel)
        return request

    @staticmethod
    async def remove_channel(request_id: int, channel_id: int):
        """Отвязать канал от задачи."""
        request = await SearchRequest.get_or_none(id=request_id)
        if not request:
            return None
        await request.channels.remove(channel_id)
        return request

    @staticmethod
    async def set_status(request_id: int, status: str):
        """Изменить статус задачи (running/paused/stopped)."""
        request = await SearchRequest.get_or_none(id=request_id)
        if not request:
            return None
        request.status = status
        await request.save()
        return request

    @staticmethod
    async def update(request_id: int, **fields):
        """Обновить поля задачи."""
        request = await SearchRequest.get_or_none(id=request_id)
        if not request:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(request, key, value)
        await request.save()
        return request

    @staticmethod
    async def delete(request_id: int):
        """Удалить задачу."""
        request = await SearchRequest.get_or_none(id=request_id)
        if not request:
            return False
        await request.delete()
        return True
