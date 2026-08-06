"""
Роуты для управления Telegram-аккаунтами: /accounts.
Все роуты требуют авторизации.
"""
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse

from src.web.common import get_user_scope
from src.web.auth import get_current_user
from src.db.models import WebUser, SearchRequest
from src.services.account import AccountService
from src.utils.logger import logger

router = APIRouter()


@router.get("/accounts", response_class=HTMLResponse)
async def accounts_list(request: Request, user: WebUser = Depends(get_current_user)):
    """Список Telegram-аккаунтов пользователя."""
    templates = request.app.state.templates
    accounts = await AccountService.get_all(user_id=user.id)
    return templates.TemplateResponse(
        request,
        "accounts/accounts.html",
        {"request": request, "user": user, "accounts": accounts},
    )


@router.get("/accounts/{account_id}", response_class=HTMLResponse)
async def account_detail(request: Request, account_id: int, user: WebUser = Depends(get_current_user)):
    """Детальная информация об одном аккаунте."""
    templates = request.app.state.templates
    account = await AccountService.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден")
    scope = await get_user_scope(user)
    if account.user_id not in scope:
        raise HTTPException(status_code=403, detail="Нет доступа к этому аккаунту")
    tasks = await SearchRequest.filter(account_id=account_id, user_id__in=scope)
    return templates.TemplateResponse(
        request,
        "accounts/account_detail.html",
        {"request": request, "user": user, "account": account, "tasks": tasks},
    )


@router.post("/accounts/create")
async def account_create(
    request: Request,
    phone: str = Form(...),
    api_id: int = Form(...),
    api_hash: str = Form(...),
    user: WebUser = Depends(get_current_user),
):
    """Создать новый аккаунт для текущего пользователя."""
    account, error = await AccountService.create(phone, api_id, api_hash, user_id=user.id)
    if error:
        return RedirectResponse(url="/accounts?error=" + error, status_code=303)
    logger.info(f"Аккаунт {phone} создан пользователем {user.telegram_id}")
    return RedirectResponse(url="/accounts", status_code=303)


@router.post("/accounts/{account_id}/toggle")
async def account_toggle(
    request: Request, account_id: int, user: WebUser = Depends(get_current_user)
):
    """Включить/отключить аккаунт."""
    account = await AccountService.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден")
    scope = await get_user_scope(user)
    if account.user_id not in scope:
        raise HTTPException(status_code=403, detail="Нет доступа")
    await AccountService.set_active(account_id, not account.is_active)
    return RedirectResponse(url="/accounts", status_code=303)


@router.post("/accounts/{account_id}/delete")
async def account_delete(
    request: Request, account_id: int, user: WebUser = Depends(get_current_user)
):
    """Удалить аккаунт (каскадно удаляет связанные задачи)."""
    account = await AccountService.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден")
    scope = await get_user_scope(user)
    if account.user_id not in scope:
        raise HTTPException(status_code=403, detail="Нет доступа")
    await AccountService.delete(account_id)
    return RedirectResponse(url="/accounts", status_code=303)