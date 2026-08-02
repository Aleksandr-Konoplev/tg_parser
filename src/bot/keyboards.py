from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.db.models import TelegramAccount, Channel, SearchRequest


# Главное меню
def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📱 Аккаунты", callback_data="accounts")
    kb.button(text="📢 Каналы", callback_data="channels")
    kb.button(text="⚙️ Задачи", callback_data="tasks")
    kb.adjust(1)  # по одной кнопке в ряд
    return kb.as_markup()


# Список аккаунтов + кнопка добавления
def accounts_kb(accounts: list[TelegramAccount]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for acc in accounts:
        status = "✅" if acc.is_active else "⛔"
        kb.button(text=f"{status} {acc.phone}", callback_data=f"account:{acc.id}")
    kb.button(text="➕ Добавить аккаунт", callback_data="account_add")
    kb.button(text="🔙 Назад", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


# Детали аккаунта: переключение статуса + удаление
def account_detail_kb(account: TelegramAccount) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    toggle = "⛔ Отключить" if account.is_active else "✅ Включить"
    kb.button(text=toggle, callback_data=f"account_toggle:{account.id}")
    kb.button(text="🗑 Удалить", callback_data=f"account_delete:{account.id}")
    kb.button(text="🔙 Назад", callback_data="accounts")
    kb.adjust(1)
    return kb.as_markup()


# ---------- Каналы ----------

# Список каналов + кнопка добавления
def channels_kb(channels: list[Channel]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for ch in channels:
        status = "✅" if ch.is_active else "⛔"
        kb.button(text=f"{status} {ch.title}", callback_data=f"channel:{ch.id}")
    kb.button(text="➕ Добавить канал", callback_data="channel_add")
    kb.button(text="🔙 Назад", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


# Детали канала: включить/отключить
def channel_detail_kb(channel: Channel) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    toggle = "✅ Включить" if not channel.is_active else "⛔ Отключить"
    kb.button(text=toggle, callback_data=f"channel_toggle:{channel.id}")
    kb.button(text="🔙 Назад", callback_data="channels")
    kb.adjust(1)
    return kb.as_markup()


# ---------- Задачи ----------

# Список задач
def tasks_kb(tasks: list[SearchRequest]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    status_icons = {"running": "▶️", "paused": "⏸", "stopped": "⏹"}
    for t in tasks:
        icon = status_icons.get(t.status, "⏹")
        kb.button(text=f"{icon} {t.name}", callback_data=f"task:{t.id}")
    kb.button(text="➕ Создать задачу", callback_data="task_add")
    kb.button(text="🔙 Назад", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


# Детали задачи + действия
def task_detail_kb(task: SearchRequest) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if task.status == "stopped" or task.status == "paused":
        kb.button(text="▶️ Запустить", callback_data=f"task_start:{task.id}")
    if task.status == "running":
        kb.button(text="⏸ Пауза", callback_data=f"task_pause:{task.id}")
        kb.button(text="⏹ Остановить", callback_data=f"task_stop:{task.id}")
    kb.button(text="🗑 Удалить", callback_data=f"task_delete:{task.id}")
    kb.button(text="🔙 Назад", callback_data="tasks")
    kb.adjust(1)
    return kb.as_markup()


