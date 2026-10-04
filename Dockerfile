# Образ для TG Parser: запускает бота (python src/main.py) и веб (python -m src.web).
# Зависимости устанавливаются через Poetry (той же версией, что сгенерировала poetry.lock).

FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=2.3.2 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

# Устанавливаем Poetry
RUN pip install "poetry==${POETRY_VERSION}"

# Копируем файлы зависимостей отдельным слоем, чтобы использовать кэш сборки Docker
COPY pyproject.toml poetry.lock ./

# Устанавливаем только зависимости (сам пакет не ставим — код запускается из src/)
RUN poetry install --no-root

# Копируем код приложения
COPY . .

EXPOSE 8000

# По умолчанию запускается бот; для веба команда переопределяется в docker-compose.yml
CMD ["python", "src/main.py"]
