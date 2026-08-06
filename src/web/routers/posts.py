"""
Роуты для просмотра постов: /posts.
Все роуты требуют авторизации.
"""
from datetime import datetime

from fastapi import APIRouter, Request, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse

from src.web.common import get_user_scope
from src.web.auth import get_current_user
from src.db.models import WebUser, Post, SearchRequest
from src.services.request import RequestService

router = APIRouter()

PAGE_SIZE = 20


@router.get("/posts", response_class=HTMLResponse)
async def posts_list(
    request: Request,
    task_id: int | None = Query(None),
    search: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    user: WebUser = Depends(get_current_user),
):
    """
    Список постов с фильтрацией по задаче, дате и тексту.
    Пагинация через offset/limit.
    Показываем только посты из задач, доступных пользователю.
    """
    templates = request.app.state.templates
    user_tasks = await RequestService.get_all(user_id=user.id, include_common=user.is_admin)
    user_task_ids = [t.id for t in user_tasks]

    if task_id is not None and task_id not in user_task_ids:
        raise HTTPException(status_code=403, detail="Нет доступа к этой задаче")

    dt_from = None
    dt_to = None
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
        except (ValueError, TypeError):
            pass

    qs = Post.filter(search_request_id__in=user_task_ids) if user_task_ids else Post.filter(id__in=[])
    if task_id is not None:
        qs = Post.filter(search_request_id=task_id)
    if dt_from is not None:
        qs = qs.filter(posted_at__gte=dt_from)
    if dt_to is not None:
        qs = qs.filter(posted_at__lte=dt_to)
    if search:
        qs = qs.filter(text__icontains=search)

    total = await qs.count()
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    offset = (page - 1) * PAGE_SIZE

    posts = (
        await qs.prefetch_related("channel", "search_request")
        .order_by("-posted_at")
        .offset(offset)
        .limit(PAGE_SIZE)
    )

    return templates.TemplateResponse(
        request,
        "posts/posts.html",
        {
            "request": request,
            "user": user,
            "tasks": user_tasks,
            "posts": posts,
            "page": page,
            "total_pages": total_pages,
            "filters": {
                "task_id": task_id or "",
                "date_from": date_from or "",
                "date_to": date_to or "",
                "search": search or "",
            },
        },
    )


@router.get("/posts/{post_id}", response_class=HTMLResponse)
async def post_detail_page(request: Request, post_id: int, user: WebUser = Depends(get_current_user)):
    """Детальный просмотр одного поста."""
    templates = request.app.state.templates
    post = await Post.get_or_none(id=post_id).prefetch_related("channel", "search_request")
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")

    scope = await get_user_scope(user)
    task = await SearchRequest.get_or_none(id=post.search_request_id) if post.search_request_id else None
    if task:
        if task.user_id not in scope:
            raise HTTPException(status_code=403, detail="Нет доступа к этому посту")
    else:
        channel = await post.channel
        if channel.user_id not in scope:
            raise HTTPException(status_code=403, detail="Нет доступа к этому посту")

    return templates.TemplateResponse(
        request,
        "posts/post_detail.html",
        {"request": request, "user": user, "post": post},
    )
