"""
Конфигурация приложения. Все настройки читаются из .env.
"""
import os
import secrets
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

# Токен Telegram бота
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Адрес БД
DB_URL = os.getenv('DB_URL', 'postgres://postgres:postgres@localhost:5432/tg_parser')

# Уровень логирования
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')

# id владельца бота
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))

# Настройки веб-интерфейса (FastAPI)
WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')  # Хост для uvicorn
WEB_PORT = int(os.getenv('WEB_PORT', '8000'))  # Порт для uvicorn

# Секретный ключ для подписи сессионных cookies веба.
# Если не задан в .env — сохраняется в .secret_key при первом запуске,
# чтобы сессии не сбрасывались при перезапуске.
_SECRET_KEY_FILE = Path(__file__).resolve().parent.parent / ".secret_key"
env_key = os.getenv("WEB_SECRET_KEY")
if env_key:
    WEB_SECRET_KEY = env_key
elif _SECRET_KEY_FILE.exists():
    WEB_SECRET_KEY = _SECRET_KEY_FILE.read_text().strip()
else:
    WEB_SECRET_KEY = secrets.token_hex(32)
    _SECRET_KEY_FILE.write_text(WEB_SECRET_KEY)

# Таймер обновления статуса задач
RESYNC_TIMER=int(os.getenv('RESYNC_TIMER', '180'))