from aiogram import Bot, Dispatcher

from src.config import BOT_TOKEN

# Глобальный объект бота — доступен во всех хендлерах
bot = Bot(token=BOT_TOKEN)
# Диспетчер — оркестрирует обработку апдейтов
dp = Dispatcher()