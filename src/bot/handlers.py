from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.dispatcher import dp
from src.bot.keyboards import (
    account_detail_kb,
    accounts_kb,
    channel_detail_kb,
    channels_kb,
    main_menu_kb,
    tasks_kb,
    task_detail_kb,
)
from src.config import ADMIN_CHAT_ID
from src.services.account import AccountService
from src.services.channel import ChannelService
from src.tg_client.auth import AuthManager
from src.bot.fsm import AddAccountStates, AddChannelStates, AddTaskStates
from src.services.request import RequestService
from aiogram.utils.keyboard import InlineKeyboardBuilder


router = Router()
dp.include_router(router)


async def is_admin(message: Message) -> bool:
    return message.from_user.id == ADMIN_CHAT_ID


# ───────────────────── /start ─────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    if not await is_admin(message):
        await message.answer("⛔ Доступ запрещён")
        return
    await message.answer("Главное меню:", reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery):
    await call.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
    await call.answer()


# ───────────────────── Аккаунты ─────────────────────

@router.callback_query(F.data == "accounts")
async def cb_accounts(call: CallbackQuery):
    accounts = await AccountService.get_all()
    text = "Список аккаунтов:" if accounts else "Аккаунтов пока нет:"
    await call.message.edit_text(text, reply_markup=accounts_kb(accounts))
    await call.answer()


@router.callback_query(F.data.startswith("account:"))
async def cb_account_detail(call: CallbackQuery):
    account_id = int(call.data.split(":")[1])
    account = await AccountService.get(account_id)
    if not account:
        await call.answer("Аккаунт не найден", show_alert=True)
        return
    text = (
        f"📱 {account.phone}\n"
        f"Статус: {'✅ активен' if account.is_active else '⛔ отключён'}\n"
        f"Сессия: {'есть' if account.session_str else 'нет'}"
    )
    await call.message.edit_text(text, reply_markup=account_detail_kb(account))
    await call.answer()


@router.callback_query(F.data == "account_add")
async def cb_account_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddAccountStates.phone)
    await call.message.edit_text("Введите номер телефона аккаунта, например +79990001122:")
    await call.answer()


@router.message(AddAccountStates.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(AddAccountStates.api_id)
    await message.answer("Введите api_id (из my.telegram.org):")


@router.message(AddAccountStates.api_id)
async def process_api_id(message: Message, state: FSMContext):
    try:
        api_id = int(message.text.strip())
    except ValueError:
        await message.answer("api_id должен быть числом. Попробуйте ещё раз:")
        return
    await state.update_data(api_id=api_id)
    await state.set_state(AddAccountStates.api_hash)
    await message.answer("Введите api_hash:")


@router.message(AddAccountStates.api_hash)
async def process_api_hash(message: Message, state: FSMContext):
    api_hash = message.text.strip()
    data = await state.get_data()
    account, err = await AccountService.create(data["phone"], data["api_id"], api_hash)
    await state.clear()
    if err:
        await message.answer(f"❌ Ошибка: {err}")
        return
    await message.answer(f"✅ Аккаунт {account.phone} добавлен")
    accounts = await AccountService.get_all()
    await message.answer("Список аккаунтов:", reply_markup=accounts_kb(accounts))


@router.callback_query(F.data.startswith("account_toggle:"))
async def cb_account_toggle(call: CallbackQuery):
    account_id = int(call.data.split(":")[1])
    account = await AccountService.get(account_id)
    if account:
        await AccountService.set_active(account_id, not account.is_active)
    await cb_account_detail(call)


@router.callback_query(F.data.startswith("account_delete:"))
async def cb_account_delete(call: CallbackQuery):
    account_id = int(call.data.split(":")[1])
    await AccountService.delete(account_id)
    await call.message.edit_text("Аккаунт удалён")
    await call.answer()


# ───────────────────── Каналы ─────────────────────

@router.callback_query(F.data == "channels")
async def cb_channels(call: CallbackQuery):
    channels = await ChannelService.get_all()
    text = "Список каналов:" if channels else "Каналов пока нет:"
    await call.message.edit_text(text, reply_markup=channels_kb(channels))
    await call.answer()


@router.callback_query(F.data.startswith("channel:"))
async def cb_channel_detail(call: CallbackQuery):
    channel_id = int(call.data.split(":")[1])
    channel = await ChannelService.get(channel_id)
    if not channel:
        await call.answer("Канал не найден", show_alert=True)
        return
    text = (
        f"📢 {channel.title}\n"
        f"Username: {channel.username or '—'}\n"
        f"Telegram ID: {channel.telegram_id}\n"
        f"Статус: {'✅ активен' if channel.is_active else '⛔ отключён'}"
    )
    await call.message.edit_text(text, reply_markup=channel_detail_kb(channel))
    await call.answer()


@router.callback_query(F.data == "channel_add")
async def cb_channel_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddChannelStates.username)
    await call.message.edit_text(
        "Введите username канала:\n"
        "Например: @channel_name или https://t.me/channel_name"
    )
    await call.answer()


@router.message(AddChannelStates.username)
async def process_channel_username(message: Message, state: FSMContext):
    raw = message.text.strip()
    username = raw.split("/")[-1].replace("@", "")
    full_username = f"@{username}"
    telegram_id = 0
    title = full_username

    # Пробуем получить информацию о канале через первый активный аккаунт с сессией
    accounts = await AccountService.get_all()
    for acc in accounts:
        if acc.is_active and acc.session_str:
            try:
                from src.tg_client.client import ClientPool
                client = await ClientPool.get_client(acc)
                entity = await client.get_entity(full_username)
                telegram_id = entity.id
                title = getattr(entity, "title", None) or full_username
                break
            except Exception:
                continue

    channel = await ChannelService.create(telegram_id, full_username, title)
    await state.clear()
    await message.answer(f"✅ Канал {title} добавлен")
    channels = await ChannelService.get_all()
    await message.answer("Список каналов:", reply_markup=channels_kb(channels))


@router.callback_query(F.data.startswith("channel_toggle:"))
async def cb_channel_toggle(call: CallbackQuery):
    channel_id = int(call.data.split(":")[1])
    channel = await ChannelService.get(channel_id)
    if channel:
        await ChannelService.update(channel_id, is_active=not channel.is_active)
    await cb_channel_detail(call)


# ───────────────────── Задачи ─────────────────────

@router.callback_query(F.data == "tasks")
async def cb_tasks(call: CallbackQuery):
    tasks = await RequestService.get_all()
    text = "Список задач:" if tasks else "Задач пока нет:"
    await call.message.edit_text(text, reply_markup=tasks_kb(tasks))
    await call.answer()


@router.callback_query(F.data.startswith("task:"))
async def cb_task_detail(call: CallbackQuery):
    task_id = int(call.data.split(":")[1])
    task = await RequestService.get(task_id)
    if not task:
        await call.answer("Задача не найдена", show_alert=True)
        return

    channels = await task.channels.all()
    channels_text = ", ".join([c.title for c in channels]) or "—"

    status_icons = {"running": "▶️", "paused": "⏸", "stopped": "⏹"}
    text = (
        f"⚙️ {task.name}\n"
        f"Статус: {status_icons.get(task.status, '⏹')} {task.status}\n"
        f"Каналы: {channels_text}\n"
        f"Интервал: {task.interval_sec}с\n"
        f"Ключевые слова: {task.keywords or '—'}"
    )
    await call.message.edit_text(text, reply_markup=task_detail_kb(task))
    await call.answer()


@router.callback_query(F.data == "task_add")
async def cb_task_add(call: CallbackQuery, state: FSMContext):
    accounts = await AccountService.get_all()
    if not accounts:
        await call.answer("Сначала добавьте хотя бы один аккаунт", show_alert=True)
        return
    await state.set_state(AddTaskStates.name)
    await call.message.edit_text("Введите название задачи:")
    await call.answer()


@router.message(AddTaskStates.name)
async def process_task_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddTaskStates.account)

    accounts = await AccountService.get_all()
    kb = InlineKeyboardBuilder()
    for acc in accounts:
        kb.button(text=acc.phone, callback_data=f"task_account:{acc.id}")
    kb.adjust(1)
    await message.answer("Выберите аккаунт для парсинга:", reply_markup=kb.as_markup())


@router.callback_query(AddTaskStates.account, F.data.startswith("task_account:"))
async def process_task_account(call: CallbackQuery, state: FSMContext):
    account_id = int(call.data.split(":")[1])
    await state.update_data(account_id=account_id)
    await state.set_state(AddTaskStates.channels)

    channels = await ChannelService.get_active()
    kb = InlineKeyboardBuilder()
    for ch in channels:
        kb.button(text=f"⬜ {ch.title}", callback_data=f"task_ch:{ch.id}")
    kb.button(text="✅ Готово", callback_data="task_channels_done")
    kb.adjust(1)
    await call.message.edit_text("Выберите каналы (нажимайте по одному, в конце «Готово»):", reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(AddTaskStates.channels, F.data.startswith("task_ch:"))
async def process_task_channel_toggle(call: CallbackQuery, state: FSMContext):
    ch_id = int(call.data.split(":")[1])
    data = await state.get_data()
    selected = data.get("selected_channels", [])
    if ch_id in selected:
        selected.remove(ch_id)
    else:
        selected.append(ch_id)
    await state.update_data(selected_channels=selected)

    # Перерисовываем клавиатуру с отметками
    channels = await ChannelService.get_active()
    kb = InlineKeyboardBuilder()
    for ch in channels:
        mark = "✅" if ch.id in selected else "⬜"
        kb.button(text=f"{mark} {ch.title}", callback_data=f"task_ch:{ch.id}")
    kb.button(text="✅ Готово", callback_data="task_channels_done")
    kb.adjust(1)
    try:
        await call.message.edit_reply_markup(reply_markup=kb.as_markup())
    except TelegramBadRequest:
        pass
    await call.answer()


@router.callback_query(AddTaskStates.channels, F.data == "task_channels_done")
async def process_task_channels_done(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("selected_channels"):
        await call.answer("Выберите хотя бы один канал", show_alert=True)
        return
    await state.set_state(AddTaskStates.keywords)
    await call.message.edit_text("Введите ключевые слова через запятую\n(или отправьте «пропустить» для парсинга всех постов):")
    await call.answer()


@router.message(AddTaskStates.keywords)
async def process_task_keywords(message: Message, state: FSMContext):
    text = message.text.strip()
    keywords = None if text.lower() in ("пропустить", "-", "") else text
    await state.update_data(keywords=keywords)
    await state.set_state(AddTaskStates.interval)
    await message.answer("Введите интервал парсинга в секундах (например 300 = 5 минут):")


@router.message(AddTaskStates.interval)
async def process_task_interval(message: Message, state: FSMContext):
    try:
        interval = int(message.text.strip())
    except ValueError:
        await message.answer("Введите число (секунды):")
        return

    data = await state.get_data()
    request = await RequestService.create(
        name=data["name"],
        account_id=data["account_id"],
        keywords=data.get("keywords"),
        interval_sec=interval,
        notify_chat_id=message.chat.id,
    )
    # Привязываем выбранные каналы
    for ch_id in data.get("selected_channels", []):
        await RequestService.add_channel(request.id, ch_id)

    await state.clear()
    await message.answer(f"✅ Задача «{request.name}» создана")
    tasks = await RequestService.get_all()
    await message.answer("Список задач:", reply_markup=tasks_kb(tasks))


# ───────────────────── Действия с задачами ─────────────────────

@router.callback_query(F.data.startswith("task_start:"))
async def cb_task_start(call: CallbackQuery):
    task_id = int(call.data.split(":")[1])
    await RequestService.set_status(task_id, "running")
    from src.services.parser import ParserManager
    ParserManager.start_request(task_id)
    await cb_task_detail(call)
    await call.answer()


@router.callback_query(F.data.startswith("task_pause:"))
async def cb_task_pause(call: CallbackQuery):
    task_id = int(call.data.split(":")[1])
    await RequestService.set_status(task_id, "paused")
    from src.services.parser import ParserManager
    await ParserManager.stop_request(task_id)
    await cb_task_detail(call)
    await call.answer()


@router.callback_query(F.data.startswith("task_stop:"))
async def cb_task_stop(call: CallbackQuery):
    task_id = int(call.data.split(":")[1])
    await RequestService.set_status(task_id, "stopped")
    from src.services.parser import ParserManager
    await ParserManager.stop_request(task_id)
    await cb_task_detail(call)
    await call.answer()


@router.callback_query(F.data.startswith("task_delete:"))
async def cb_task_delete(call: CallbackQuery):
    task_id = int(call.data.split(":")[1])
    from src.services.parser import ParserManager
    await ParserManager.stop_request(task_id)
    await RequestService.delete(task_id)
    await call.message.edit_text("Задача удалена")
    await call.answer()


# ───────────────────── Ввод кода авторизации ─────────────────────
# Ловим сообщения, похожие на код (4-6 цифр), когда есть запрос

@router.message(F.text.regexp(r"^\d{4,6}$"))
async def handle_auth_code(message: Message):
    from src.tg_client.auth import _pending_codes
    if not _pending_codes:
        return  # код не запрашивали — пропускаем, может быть FSM

    code = message.text.strip()
    account_id, _ = next(iter(_pending_codes.items()))  # берём первый
    ok = await AuthManager.submit_code(account_id, code)
    if ok:
        await message.answer("✅ Код принят, продолжаю авторизацию")
    else:
        await message.answer("❌ Не удалось отправить код")