import sys
# Loguru — современная замена стандартному logging
# Автоматически форматирует, раскрашивает и структурирует логи
from loguru import logger as _logger
from src.config import LOG_LEVEL

# Удаляем стандартный вывод (вывод по умолчанию)
_logger.remove()
# Добавляем вывод в stderr с нужным уровнем логирования
_logger.add(sys.stderr, level=LOG_LEVEL)
# Экспортируем настроенный логгер для использования в других модулях
logger = _logger