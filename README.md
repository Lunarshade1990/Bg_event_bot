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
- Docker Compose для PostgreSQL, backend, bot и миграций
- базовые точки входа backend и bot
- стартовая тестовая инфраструктура

## Запуск всего стека в Docker

Этот вариант ближе к будущему запуску на VPS: `postgres`, одноразовый контейнер миграций,
`backend` и `bot` поднимаются одной командой.

1. Подготовить `.env` в корне проекта. Реальные значения хранятся только локально:

```powershell
Copy-Item .env.example .env
```

Минимально нужны:

- `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `TELEGRAM_BOT_TOKEN`
- `INTERNAL_API_TOKEN`
- `TELEGRAM_TOPIC_NAME`

Для Docker не нужно менять `DB_HOST` и `BACKEND_BASE_URL` в `.env`: compose сам передает
контейнерам внутренние значения `DB_HOST=postgres` и `BACKEND_BASE_URL=http://backend:8000`.

2. Собрать и запустить сервисы:

```powershell
docker compose --env-file .env -f docker/docker-compose.yml up -d --build
```

3. Проверить состояние:

```powershell
docker compose --env-file .env -f docker/docker-compose.yml ps
docker compose --env-file .env -f docker/docker-compose.yml logs -f backend
docker compose --env-file .env -f docker/docker-compose.yml logs -f bot
```

4. Остановить сервисы:

```powershell
docker compose --env-file .env -f docker/docker-compose.yml down
```

PostgreSQL хранит данные в именованном Docker volume `docker_postgres_data`. Старый локальный
каталог `docker/postgres/data` больше не используется этим compose-файлом.

## Что будет следующим шагом

- SQLAlchemy-модели
- Alembic-миграции
- первая версия API
- затем сценарии бота
