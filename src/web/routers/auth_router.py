"""
Роуты аутентификации: /login, /verify, /logout.
Не требуют авторизации (кроме /logout).
"""
from fastapi import APIRouter, Request, Form, Query, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse

from src.web.auth import (
    get_current_user,
    create_session,
    request_login_code,
    verify_login_code,
    SESSION_COOKIE_NAME,
)

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа. Если уже аутентифицирован — редирект на /."""
    try:
        user = await get_current_user(request)
        if user:
            return RedirectResponse(url="/", status_code=303)
    except HTTPException:
        pass
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "login.html", {"request": request})


@router.post("/login")
async def login_submit(request: Request, username: str = Form(...)):
    """Обработка формы входа. Отправляет одноразовый код в Telegram."""
    templates = request.app.state.templates
    raw = username.strip()
    if raw.startswith("@"):
        return templates.TemplateResponse(request, "login.html", {
            "request": request,
            "error": "Введите числовой Telegram ID (можно узнать у @userinfobot). "
                     "Username будет привязан после входа.",
        })
    try:
        telegram_id = int(raw)
    except ValueError:
        return templates.TemplateResponse(request, "login.html", {
            "request": request,
            "error": "Введите числовой Telegram ID.",
        })

    success, message = await request_login_code(telegram_id)
    if not success:
        return templates.TemplateResponse(request, "login.html", {
            "request": request,
            "error": message,
        })

    return templates.TemplateResponse(request, "verify.html", {
        "request": request,
        "telegram_id": telegram_id,
        "message": message,
    })


@router.get("/verify", response_class=HTMLResponse)
async def verify_page(request: Request, telegram_id: int = Query(...)):
    """Страница ввода кода."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "verify.html", {
        "request": request,
        "telegram_id": telegram_id,
    })


@router.post("/verify")
async def verify_submit(request: Request, telegram_id: int = Form(...), code: str = Form(...)):
    """Проверка кода авторизации. При успехе — создаёт сессию и редиректит на /."""
    templates = request.app.state.templates
    success, message, user = await verify_login_code(telegram_id, code)
    if not success:
        return templates.TemplateResponse(request, "verify.html", {
            "request": request,
            "telegram_id": telegram_id,
            "error": message,
        })

    session_token = create_session(user.id)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=False,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    """Выход: удаляем cookie сессии."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response