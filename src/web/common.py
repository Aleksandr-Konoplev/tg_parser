"""
Общие утилиты для роутеров веб-интерфейса.
Вынесены в отдельный модуль, чтобы избежать циклических импортов.
"""
from pathlib import Path

from src.db.models import WebUser

# Путь к корню проекта (на 3 уровня выше src/web/common.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


async def get_user_scope(user: WebUser) -> list[int | None]:
    """
    Возвращает список user_id для фильтрации запросов.
    Админ (is_admin=True) видит свои данные + данные без владельца (user_id IS NULL).
    Обычный пользователь — только свои.
    """
    if user.is_admin:
        return [user.id, None]
    return [user.id]