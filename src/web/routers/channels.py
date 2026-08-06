"""
Роуты для управления каналами: /channels.
Все роуты требуют авторизации.
"""
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse

from src.web.common import get_user_scope
from src.web.auth import get_current_user
from src.db.models import WebUser, TelegramAccount, SearchRequest, Post
from src.services.account import AccountService
from src.services.channel import ChannelService
from src.tg_client.client import ClientPool
from src.utils.logger import logger

router = APIRouter()


@router.get("/channels", response_class=HTMLResponse)
async def channels_list(request: Request, user: WebUser = Depends(get_current_user)):
    """Список каналов пользователя."""
    templates = request.app.state.templates
    accounts = await AccountService.get_all(user_id=user.id)
    channels = await ChannelService.get_all(user_id=user.id)
    return templates.TemplateResponse(
        request,
        "channels/channels.html",
        {"request": request, "user": user, "channels": channels, "accounts": accounts},
    )


@router.get("/channels/{channel_id}", response_class=HTMLResponse)
async def channel_detail(request: Request, channel_id: int, user: WebUser = Depends(get_current_user)):
    """Детальная информация об одном канале."""
    templates = request.app.state.templates
    channel = await ChannelService.get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")
    scope = await get_user_scope(user)
    if channel.user_id not in scope:
        raise HTTPException(status_code=403, detail="Нет доступа к этому каналу")
    tasks = await SearchRequest.filter(channels__channel=channel_id, user_id__in=scope)
    posts_count = await Post.filter(channel_id=channel_id).count()
    return templates.TemplateResponse(
        request,
        "channels/channel_detail.html",
        {
            "request": request, "user": user,
            "channel": channel, "tasks": tasks, "posts_count": posts_count,
        },
    )


@router.post("/channels/create")
async def channel_create(
    request: Request,
    identifier: str = Form(...),
    account_id: int = Form(...),
    user: WebUser = Depends(get_current_user),
):
    """Создать новый канал. identifier резолвится через Telethon."""
    templates = request.app.state.templates
    raw = identifier.strip()
    clean_username = raw.split("/")[-1].replace("@", "")
    full_username = f"@{clean_username}"

    account = await TelegramAccount.get_or_none(id=account_id)
    if not account:
        return RedirectResponse(url="/channels?error=Аккаунт не найден", status_code=303)
    scope = await get_user_scope(user)
    if account.user_id not in scope:
        raise HTTPException(status_code=403, detail="Нет доступа к этому аккаунту")
    if not account.session_str:
        return RedirectResponse(url="/channels?error=Аккаунт не авторизован (нет сессии)", status_code=303)

    telegram_id = 0
    title = clean_username
    try:
        client = await ClientPool.get_client(account)
        entity = await client.get_entity(full_username)
        telegram_id = entity.id
        title = getattr(entity, "title", None) or clean_username
    except Exception as e:
        logger.warning(f"Не удалось резолвнуть {full_username}: {e}")
        return RedirectResponse(
            url=f"/channels?error=Не удалось найти канал: {e}",
            status_code=303,
        )

    channel = await ChannelService.create(telegram_id, clean_username, title, user_id=user.id)
    logger.info(f"Канал {title} создан пользователем {user.telegram_id}")
    return RedirectResponse(url="/channels", status_code=303)


@router.post("/channels/{channel_id}/toggle")
async def channel_toggle(
    request: Request, channel_id: int, user: WebUser = Depends(get_current_user)
):
    """Включить/отключить канал."""
    channel = await ChannelService.get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")
    scope = await get_user_scope(user)
    if channel.user_id not in scope:
        raise HTTPException(status_code=403, detail="Нет доступа")
    await ChannelService.update(channel_id, is_active=not channel.is_active)
    return RedirectResponse(url="/channels", status_code=303)


@router.post("/channels/{channel_id}/delete")
async def channel_delete(
    request: Request, channel_id: int, user: WebUser = Depends(get_current_user)
):
    """Мягкое удаление канала."""
    channel = await ChannelService.get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")
    scope = await get_user_scope(user)
    if channel.user_id not in scope:
        raise HTTPException(status_code=403, detail="Нет доступа")
    await ChannelService.delete(channel_id)
    return RedirectResponse(url="/channels", status_code=303)