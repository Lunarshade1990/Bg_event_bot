# boardgames_meetup_bot

Небольшой сервис для организации встреч на настольные игры.

Проект разделен на две части:

- `backend` — внутреннее API на `FastAPI`, `SQLAlchemy`, `PostgreSQL`
- `bot` — Telegram-бот на `aiogram`

## Стек

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- aiogram 3
- pytest

## Быстрый старт

1. Создать виртуальное окружение и установить зависимости:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
```

2. Скопировать шаблон окружения:

```powershell
Copy-Item .env.example .env
```

3. Запустить PostgreSQL в Docker:

```powershell
docker compose -f docker/docker-compose.yml up -d
```

4. Запустить backend:

```powershell
uvicorn backend.app.main:app --reload
```

5. Запустить бота:

```powershell
python -m bot.app.main
```

## Что уже подготовлено

- каркас проекта
- безопасная конфигурация через переменные окружения
- Docker Compose для PostgreSQL
- базовые точки входа backend и bot
- стартовая тестовая инфраструктура

## Что будет следующим шагом

- SQLAlchemy-модели
- Alembic-миграции
- первая версия API
- затем сценарии бота
