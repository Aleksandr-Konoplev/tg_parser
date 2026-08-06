"""Модуль аутентификации для веб-интерфейса."""
import random
from datetime import datetime, timedelta, timezone

from fastapi import Request, HTTPException
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from src.config import WEB_SECRET_KEY, BOT_TOKEN
from src.db.models import WebUser, AuthCode


# Создаём сериализатор для подписи cookies
# Использует WEB_SECRET_KEY — если ключ меняется, все сессии становятся недействительными
_serializer = URLSafeTimedSerializer(WEB_SECRET_KEY, salt="web-session")

# Название cookie для сессии
SESSION_COOKIE_NAME = "session"
# Срок жизни сессии — 7 дней
SESSION_MAX_AGE = 7 * 24 * 60 * 60


def _generate_code() -> str:
    """Генерирует 6-значный код для входа."""
    return str(random.randint(100000, 999999))


def create_session(web_user_id: int) -> str:
    """
    Создаёт signed cookie для пользователя.

    Args:
        web_user_id: ID пользователя в таблице WebUser.

    Returns:
        Строка cookie для установки в ответ.
    """
    data = {"user_id": web_user_id}
    return _serializer.dumps(data)


def get_session_data(request: Request) -> dict | None:
    """
    Достаёт данные из signed cookie запроса.

    Args:
        request: Запрос FastAPI.

    Returns:
        Словарь с user_id или None если cookie нет/недействительна.
    """
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        return None
    try:
        # max_age — максимальный возраст подписи в секундах
        return _serializer.loads(cookie, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


async def get_current_user(request: Request) -> WebUser:
    """
    FastAPI dependency: достаёт текущего пользователя из сессионной cookie.

    Вызывается как Depends(get_current_user) в защищённых роутах.
    Если пользователь не аутентифицирован — поднимает 401.

    Args:
        request: Запрос FastAPI.

    Returns:
        Объект WebUser.

    Raises:
        HTTPException: 401 если пользователь не аутентифицирован.
    """
    session_data = get_session_data(request)
    if session_data is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await WebUser.get_or_none(id=session_data["user_id"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def send_auth_code_via_bot(telegram_id: int, code: str) -> bool:
    """
    Отправляет код авторизации пользователю в Telegram через Bot API.

    Использует прямой вызов Telegram Bot API (без aiogram).
    Это позволяет веб-процессу отправлять сообщения независимо от бота.

    Args:
        telegram_id: ID пользователя в Telegram.
        code: 6-значный код для входа.

    Returns:
        True если сообщение отправлено, False если произошла ошибка.
    """
    import httpx

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": telegram_id,
        "text": (
            f"🔐 Код для входа в веб-интерфейс tg-parser:\n\n"
            f"<code>{code}</code>\n\n"
            f"Код действителен 5 минут. Никому его не сообщайте."
        ),
        "parse_mode": "HTML",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception:
        return False


async def get_or_create_web_user(telegram_id: int, username: str | None = None,
                                  chat_id: int | None = None) -> WebUser:
    """
    Создаёт или достаёт существующего пользователя веб-интерфейса.

    Если пользователь с таким telegram_id уже существует — обновляет
    username и chat_id (могли измениться).

    Args:
        telegram_id: ID пользователя в Telegram.
        username: @username в Telegram.
        chat_id: chat_id для отправки сообщений.

    Returns:
        Объект WebUser.
    """
    user, created = await WebUser.get_or_create(
        telegram_id=telegram_id,
        defaults={
            "username": username,
            "chat_id": chat_id,
            "is_admin": False,
        },
    )
    if not created:
        # Обновляем username/chat_id если изменились
        needs_update = False
        if username and user.username != username:
            user.username = username
            needs_update = True
        if chat_id and user.chat_id != chat_id:
            user.chat_id = chat_id
            needs_update = True
        if needs_update:
            await user.save()
    return user


async def request_login_code(telegram_id: int, username: str | None = None) -> tuple[bool, str]:
    """
    Полный процесс запроса кода для входа.

    1. Генерирует код
    2. Сохраняет AuthCode в БД
    3. Отправляет код через Bot API

    Args:
        telegram_id: ID пользователя в Telegram.
        username: @username (опционально, для создания WebUser).

    Returns:
        (успех, сообщение).
    """
    # Генерируем код
    code = _generate_code()

    # Сохраняем в БД (срок жизни — 5 минут)
    await AuthCode.create(
        telegram_id=telegram_id,
        code=code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    # Отправляем через бота
    sent = await send_auth_code_via_bot(telegram_id, code)
    if not sent:
        return False, "Не удалось отправить код в Telegram. Проверьте, что бот может писать вам."

    return True, "Код отправлен в Telegram! Проверьте сообщения от бота."


async def verify_login_code(telegram_id: int, code: str) -> tuple[bool, str, WebUser | None]:
    """
    Проверяет код авторизации и создаёт/возвращает пользователя.

    1. Ищет неиспользованный, неистёкший код
    2. Помечает его как использованный
    3. Создаёт/достаёт WebUser

    Args:
        telegram_id: ID пользователя в Telegram.
        code: 6-значный код.

    Returns:
        (успех, сообщение, WebUser или None).
    """
    now = datetime.now(timezone.utc)

    # Ищем действующий код
    auth_code = await AuthCode.filter(
        telegram_id=telegram_id,
        code=code,
        is_used=False,
        expires_at__gt=now,
    ).first()

    if not auth_code:
        return False, "Неверный или истёкший код.", None

    # Помечаем как использованный
    auth_code.is_used = True
    await auth_code.save()

    # Создаём или получаем пользователя
    user = await get_or_create_web_user(telegram_id)

    return True, "Вход выполнен успешно!", user

