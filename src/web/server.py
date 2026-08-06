"""
FastAPI веб-сервер для администрирования TG Parser.

Тонкий слой: создаёт app, настраивает статику и шаблоны,
добавляет обработчик 401 → /login, подключает роутеры.

Запуск: python -m src.web
"""
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.web.common import get_user_scope, BASE_DIR
from src.web.auth import get_current_user
from src.db.models import WebUser, TelegramAccount, Channel, SearchRequest, Post
from tortoise.expressions import Q

# ───────────────────── Создание приложения ─────────────────────

app = FastAPI(title="TG Parser Admin")

# Подключаем статику
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Сохраняем Jinja2Templates в app.state — так его получат все роутеры
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.state.templates = templates


# ───────────────────── Обработчик 401 → /login ─────────────────────

@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    """Редирект на /login при неаутентифицированном доступе."""
    if exc.status_code == 401:
        return RedirectResponse(url="/login")
    return HTMLResponse(str(exc.detail), status_code=exc.status_code)


# ───────────────────── Подключение роутеров ─────────────────────

from src.web.routers.auth_router import router as auth_router
from src.web.routers.accounts import router as accounts_router
from src.web.routers.channels import router as channels_router
from src.web.routers.tasks import router as tasks_router
from src.web.routers.posts import router as posts_router

app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(channels_router)
app.include_router(tasks_router)
app.include_router(posts_router)


# ───────────────────── Dashboard ─────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user: WebUser = Depends(get_current_user)):
    """Главная страница со сводной статистикой пользователя."""
    scope = await get_user_scope(user)

    owner_filter = Q(user_id=user.id)
    if user.is_admin:
        owner_filter |= Q(user_id__isnull=True)
    accounts_count = await TelegramAccount.filter(owner_filter).count()
    channels_count = await Channel.filter(owner_filter).count()
    tasks = await SearchRequest.filter(owner_filter)

    task_ids = [t.id for t in tasks]
    if task_ids:
        posts_count = await Post.filter(search_request_id__in=task_ids).count()
        recent_posts = (
            await Post.filter(search_request_id__in=task_ids)
            .prefetch_related("channel", "search_request")
            .order_by("-parsed_at")
            .limit(10)
        )
    else:
        posts_count = 0
        recent_posts = []

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "stats": {
                "accounts_count": accounts_count,
                "channels_count": channels_count,
                "tasks_count": len(tasks),
                "posts_count": posts_count,
            },
            "recent_posts": recent_posts,
        },
    )
