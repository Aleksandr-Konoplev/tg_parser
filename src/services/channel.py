from src.db.models import Channel
from src.utils.logger import logger


class ChannelService:

    @staticmethod
    async def create(telegram_id: int, username: str | None, title: str):
        # Telegram ID может быть отрицательным числом (private supergroups/channels)
        channel = await Channel.create(
            telegram_id=telegram_id,
            username=username,
            title=title,
        )
        logger.info(f"Канал создан: {username or telegram_id}")
        return channel

    @staticmethod
    async def get(channel_id: int):
        return await Channel.get_or_none(id=channel_id)

    @staticmethod
    async def get_by_telegram_id(telegram_id: int):
        return await Channel.get_or_none(telegram_id=telegram_id)

    @staticmethod
    async def get_active():
        return await Channel.filter(is_active=True).order_by("id")

    @staticmethod
    async def get_all():
        return await Channel.all().order_by("id")

    @staticmethod
    async def update(channel_id: int, **fields):
        channel = await ChannelService.get(channel_id)
        if not channel:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(channel, key, value)
        await channel.save()
        return channel

    # @staticmethod
    # async def delete(channel_id: int):
    #     channel = await ChannelService.get(channel_id)
    #     if not channel:
    #         return False
    #     await channel.delete()
    #     return True

    @staticmethod
    async def delete(channel_id: int):
        channel = await ChannelService.get(channel_id)
        if not channel:
            return False
        channel.is_active = False
        await channel.save(update_fields=["is_active"])
        logger.info(f"Канал {channel_id} отключён (soft delete)")
        return True