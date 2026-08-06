"""
Роуты для управления задачами парсинга: /tasks.
Все роуты требуют авторизации.
"""
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse

from src.web.common import get_user_scope
from src.web.auth import get_current_user
from src.db.models import WebUser, TelegramAccount, Post
from src.services.account import AccountService
from src.services.channel import ChannelService
from src.services.request import RequestService
from src.services.parser import ParserManager
from src.utils.logger import logger

router = APIRouter()


@router.get("/tasks", response_class=HTMLResponse)
async def tasks_list(request: Request, user: WebUser = Depends(get_current_user)):
    """Список задач парсинга пользователя."""
    templates = request.app.state.templates
    tasks = await RequestService.get_all(user_id=user.id)
    tasks_data = []
    for t in tasks:
        channels = await t.channels.all()
        tasks_data.append({
            "id": t.id,
            "name": t.name,
            "account": await t.account,
            "channel_count": len(channels),
            "interval_sec": t.interval_sec,
            "status": t.status,
            "last_run_at": t.last_run_at,
            "created_at": t.created_at,
        })
    return templates.TemplateResponse(
        request,
        "tasks/tasks.html",
        {"request": request, "user": user, "tasks": tasks_data},
    )


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
async def task_detail(request: Request, task_id: int, user: WebUser = Depends(get_current_user)):
    """Детальная информация о задаче."""
    templates = request.app.state.templates
    task = await RequestService.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    scope = await get_user_scope(user)
    if task.user_id not in scope:
        raise HTTPException(status_code=403, detail="Нет доступа к этой задаче")
    channels = await task.channels.all()
    posts_count = await Post.filter(search_request_id=task_id).count()
    return templates.TemplateResponse(
        request,
        "tasks/task_detail.html",
        {
            "request": request, "user": user,
            "task": task, "channels": channels,
            "posts_count": posts_count,
        },
    )


@router.get("/tasks/create", response_class=HTMLResponse)
async def task_create_form(request: Request, user: WebUser = Depends(get_current_user)):
    """Форма создания новой задачи."""
    templates = request.app.state.templates
    accounts = await AccountService.get_all(user_id=user.id)
    channels = await ChannelService.get_active(user_id=user.id)
    return templates.TemplateResponse(
        request,
        "tasks/task_create.html",
        {"request": request, "user": user, "accounts": accounts, "channels": channels},
    )


@router.post("/tasks/create")
async def task_create(
    request: Request,
    name: str = Form(...),
    account_id: int = Form(...),
    keywords: str = Form(""),
    interval_sec: int = Form(300),
    limit_per_run: int = Form(50),
    notify_chat_id: int | None = Form(None),
    channel_ids: list[int] = Form([]),
    user: WebUser = Depends(get_current_user),
):
    """Создать новую задачу парсинга для текущего пользователя."""
    templates = request.app.state.templates
    account = await TelegramAccount.get_or_none(id=account_id)
    if not account:
        return RedirectResponse(url="/tasks/create?error=Аккаунт не найден", status_code=303)
    scope = await get_user_scope(user)
    if account.user_id not in scope:
        raise HTTPException(status_code=403, detail="Нет доступа к аккаунту")

    request_obj = await RequestService.create(
        name=name,
        account_id=account_id,
        keywords=keywords or None,
        interval_sec=interval_sec,
        limit_per_run=limit_per_run,
        notify_chat_id=notify_chat_id,
        user_id=user.id,
    )
    for ch_id in channel_ids:
        await RequestService.add_channel(request_obj.id, ch_id)

    logger.info(f"Задача «{name}» создана пользователем {user.telegram_id}")
    return RedirectResponse(url="/tasks", status_code=303)


@router.post("/tasks/{task_id}/start")
async def task_start(
    request: Request, task_id: int, user: WebUser = Depends(get_current_user)
):
    """Запустить задачу парсинга."""
    task = await RequestService.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    scope = await get_user_scope(user)
    if task.user_id not in scope:
        raise HTTPException(status_code=403, detail="Нет доступа")
    await RequestService.set_status(task_id, "running")
    ParserManager.start_request(task_id)
    logger.info(f"Задача {task_id} запущена пользователем {user.telegram_id}")
    return RedirectResponse(url="/tasks", status_code=303)


@router.post("/tasks/{task_id}/pause")
async def task_pause(
    request: Request, task_id: int, user: WebUser = Depends(get_current_user)
):
    """Поставить задачу на паузу."""
    task = await RequestService.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    scope = await get_user_scope(user)
    if task.user_id not in scope:
        raise HTTPException(status_code=403, detail="Нет доступа")
    await RequestService.set_status(task_id, "paused")
    await ParserManager.stop_request(task_id)
    return RedirectResponse(url="/tasks", status_code=303)


@router.post("/tasks/{task_id}/stop")
async def task_stop(
    request: Request, task_id: int, user: WebUser = Depends(get_current_user)
):
    """Остановить задачу."""
    task = await RequestService.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    scope = await get_user_scope(user)
    if task.user_id not in scope:
        raise HTTPException(status_code=403, detail="Нет доступа")
    await RequestService.set_status(task_id, "stopped")
    await ParserManager.stop_request(task_id)
    return RedirectResponse(url="/tasks", status_code=303)


@router.post("/tasks/{task_id}/delete")
async def task_delete(
    request: Request, task_id: int, user: WebUser = Depends(get_current_user)
):
    """Удалить задачу."""
    task = await RequestService.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    scope = await get_user_scope(user)
    if task.user_id not in scope:
        raise HTTPException(status_code=403, detail="Нет доступа")
    await ParserManager.stop_request(task_id)
    await RequestService.delete(task_id)
    return RedirectResponse(url="/tasks", status_code=303)