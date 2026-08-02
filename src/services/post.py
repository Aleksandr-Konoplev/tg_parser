"""Сервис для чтения и форматирования постов из базы."""

from datetime import datetime
from typing import Sequence

from src.db.models import Post


class PostService:
    """
    Операции для вывода сохранённых постов в Telegram-боте.
    """

    # Количество постов, выводимых на одной странице бота
    PAGE_SIZE: int = 5

    @staticmethod
    async def get_posts(
        request_id: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = PAGE_SIZE,
        offset: int = 0,
    ) -> Sequence[Post]:
        """
        Возвращает посты заданной задачи.

        Если переданы date_from и date_to — фильтрует по posted_at.
        Если даты не переданы — возвращает все сохранённые посты задачи.

        Args:
            request_id: ID задачи парсинга (SearchRequest).
            date_from: Начало периода (включительно), timezone-aware UTC, или None.
            date_to: Конец периода (включительно), timezone-aware UTC, или None.
            limit: Максимальное количество постов на странице.
            offset: Смещение для пагинации.

        Returns:
            Список постов, отсортированных от новых к старым.
        """
        qs = Post.filter(search_request_id=request_id)
        if date_from is not None:
            qs = qs.filter(posted_at__gte=date_from)
        if date_to is not None:
            qs = qs.filter(posted_at__lte=date_to)
        return (
            await qs.prefetch_related("channel")
            .order_by("-posted_at")
            .offset(offset)
            .limit(limit)
        )

    @staticmethod
    async def count_posts(
        request_id: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        """
        Возвращает общее количество постов задачи.

        Если переданы даты — учитывает только посты за указанный период.
        """
        qs = Post.filter(search_request_id=request_id)
        if date_from is not None:
            qs = qs.filter(posted_at__gte=date_from)
        if date_to is not None:
            qs = qs.filter(posted_at__lte=date_to)
        return await qs.count()

    @staticmethod
    def build_public_link(channel_username: str | None, msg_id: int) -> str | None:
        """
        Формирует публичную ссылку на пост вида https://t.me/username/msg_id.

        Для приватных каналов (без username) ссылка не формируется.
        """
        if not channel_username:
            return None
        username = channel_username.lstrip("@")
        if not username:
            return None
        return f"https://t.me/{username}/{msg_id}"

    @staticmethod
    def format_post(post: Post, max_text_len: int = 3000) -> str:
        """
        Превращает объект Post в текст сообщения для отправки в Telegram.

        Очень длинные тексты обрезаются, чтобы не превысить лимит сообщения.
        """
        channel_title = post.channel.title if post.channel else "—"
        date_str = post.posted_at.strftime("%d.%m.%Y %H:%M") if post.posted_at else "—"

        link = PostService.build_public_link(
            post.channel.username if post.channel else None,
            post.telegram_msg_id,
        )
        link_str = f"🔗 {link}" if link else "🔗 ссылка недоступна для приватного канала"

        text = post.text or "—"
        if len(text) > max_text_len:
            text = text[:max_text_len].rstrip() + "…"

        return (
            f"📢 Канал: {channel_title}\n"
            f"🕐 {date_str}\n"
            f"{link_str}\n\n"
            f"{text}"
        )
