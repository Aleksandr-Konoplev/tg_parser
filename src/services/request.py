from src.db.models import SearchRequest
from src.utils.logger import logger


class RequestService:

    @staticmethod
    async def create(name: str, account_id: int, keywords: str | None = None,
                     interval_sec: int = 300, limit_per_run: int = 50,
                     notify_chat_id: int | None = None):
        request = await SearchRequest.create(
            name=name,
            account_id=account_id,
            keywords=keywords,
            interval_sec=interval_sec,
            limit_per_run=limit_per_run,
            notify_chat_id=notify_chat_id,
        )
        return request

    @staticmethod
    async def get(request_id: int):
        return await SearchRequest.get_or_none(id=request_id)

    @staticmethod
    async def get_all():
        return await SearchRequest.all().order_by("-id")

    # Активные задачи — их обрабатывает планировщик парсера
    @staticmethod
    async def get_running():
        return await SearchRequest.filter(status="running")

    @staticmethod
    async def add_channel(request_id: int, channel_id: int):
        request = await SearchRequest.get_or_none(id=request_id)
        if not request:
            return None
        await request.channels.add(channel_id)  # Tortoise M2M: add принимает id или объект
        return request

    @staticmethod
    async def remove_channel(request_id: int, channel_id: int):
        request = await SearchRequest.get_or_none(id=request_id)
        if not request:
            return None
        await request.channels.remove(channel_id)
        return request

    @staticmethod
    async def set_status(request_id: int, status: str):
        request = await SearchRequest.get_or_none(id=request_id)
        if not request:
            return None
        request.status = status
        await request.save()
        return request

    @staticmethod
    async def update(request_id: int, **fields):
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
        request = await SearchRequest.get_or_none(id=request_id)
        if not request:
            return False
        await request.delete()
        return True