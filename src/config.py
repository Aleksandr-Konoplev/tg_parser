import os
from dotenv import load_dotenv


load_dotenv()

# Токен Telegram бота
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Адрес БД
DB_URL = os.getenv('DB_URL', 'postgres://postgres:postgres@localhost:5432/tg_parser')

# Уровень логирования
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')