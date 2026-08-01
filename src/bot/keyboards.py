from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.db.models import TelegramAccount


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