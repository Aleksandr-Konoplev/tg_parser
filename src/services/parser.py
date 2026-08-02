import asyncio
from datetime import datetime, timezone

from tortoise.exceptions import IntegrityError

from src.db.models import Post, SearchRequest
from src.services.request import RequestService
from src.tg_client.client import ClientPool
from src.utils.logger import logger


# Менеджер парсера: держит фоновые asyncio-задачи по одной на каждый активный SearchRequest.
# Ключ словаря — request.id, значение — корутина цикличного парсинга.
class ParserManager:

    _tasks: dict[int, asyncio.Task] = {}

    # Синхронизация при старте приложения:
    # для всех задач со статусом "running" поднимаем фоновый цикл парсинга
    @classmethod
    async def sync_with_db(cls):
        running = await RequestService.get_running()
        for request in running:
            cls.start_request(request.id)

    # Запустить фоновый цикл для задачи
    @classmethod
    def start_request(cls, request_id: int):
        if request_id in cls._tasks:
            return  # уже запущена
        task = asyncio.create_task(cls._run_loop(request_id))
        cls._tasks[request_id] = task
        logger.info(f"Парсинг задачи {request_id} запущен")

    # Остановить фоновый цикл для задачи
    @classmethod
    async def stop_request(cls, request_id: int):
        task = cls._tasks.pop(request_id, None)
        if task:
            task.cancel()  # прерываем цикл
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info(f"Парсинг задачи {request_id} остановлен")

    # Бесконечный цикл: парсим → спим interval_sec → повторяем
    @classmethod
    async def _run_loop(cls, request_id: int):
        while True:
            request = await RequestService.get(request_id)
            if not request or request.status != "running":
                break
            try:
                await cls._parse_once(request)
            except Exception as e:
                logger.error(f"Задача {request_id}: необработанная ошибка {e}")
            await asyncio.sleep(request.interval_sec)

    # Один проход парсинга по задаче
    @classmethod
    async def _parse_once(cls, request: SearchRequest):
        # Аккаунт задачи должен быть активным, иначе пропускаем
        account = await request.account
        if not account.is_active:
            logger.warning(f"Задача {request.id}: аккаунт {account.phone} неактивен, пропуск")
            return

        # Каналы задачи: только активные (soft delete учтён)
        channels = await request.channels.all()
        active_channels = [ch for ch in channels if ch.is_active]

        for channel in active_channels:
            try:
                await cls._parse_channel(request, account, channel)
            except Exception as e:
                # Ошибка одного канала не должна ронять всю задачу
                logger.error(f"Задача {request.id}, канал {channel}: {e}")

        request.last_run_at = datetime.now(timezone.utc)
        await request.save(update_fields=["last_run_at"])


    @classmethod
    async def _parse_channel(cls, request, account, channel):
        # Последний уже распарсенный msg_id — с него начнём (не включая его)
        last_post = (
            await Post.filter(channel=channel, search_request=request)
            .order_by("-telegram_msg_id")
            .first()
        )
        offset_id = last_post.telegram_msg_id if last_post else None

        # На что резолвить канал: @username если есть, иначе числовой telegram_id
        channel_ref = f"@{channel.username}" if channel.username else channel.telegram_id

        messages = await ClientPool.get_messages(account, channel_ref, limit=request.limit_per_run, offset_id=offset_id)

        new_posts = 0
        for msg in messages:
            text = msg.text or ""
            # Фильтр по ключевым словам (keywords через запятую, пусто = все посты)
            if request.keywords and not cls._matches_keywords(text, request.keywords):
                continue

            try:
                # get_or_create — защита от дублей, если канал в нескольких задачах
                _, created = await Post.get_or_create(
                    telegram_msg_id=msg.id,
                    channel=channel,
                    defaults={
                        "search_request": request,
                        "text": text or None,
                        "media_info": cls._extract_media(msg),
                        "views": getattr(msg, "views", None),
                        "forwards": getattr(msg, "forwards", None),
                        "replies": getattr(msg, "replies", None),
                    },
                )
                if created:
                    new_posts += 1
            except IntegrityError:
                continue  # уже существует — пропускаем

        logger.info(f"Задача {request.id}, канал {channel}: новых постов {new_posts}")
        if new_posts > 0 and request.notify_chat_id:
            from src.bot.dispatcher import bot
            try:
                await bot.send_message(
                    request.notify_chat_id,
                    f"📢 {channel.title}: {new_posts} новых постов",
                )
            except Exception as send_err:
                logger.error(f"Ошибка отправки уведомления: {send_err}")


    # True если текст содержит хотя бы одно из ключевых слов (без учёта регистра)
    @staticmethod
    def _matches_keywords(text: str, keywords: str) -> bool:
        words = [w.strip().lower() for w in keywords.split(",") if w.strip()]
        lower_text = text.lower()
        return any(w in lower_text for w in words)

    # Собираем JSON-описание медиа (тип + размер), без скачивания файлов
    @staticmethod
    def _extract_media(msg) -> dict | None:
        media = getattr(msg, "media", None)
        if not media:
            return None
        info = {"type": type(media).__name__}
        doc = getattr(media, "document", None)
        if doc:
            info["size"] = getattr(doc, "size", None)
            info["mime_type"] = getattr(doc, "mime_type", None)
        return info