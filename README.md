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

## Безопасный запуск на VPS

Бот использует Telegram long polling, поэтому входящие подключения к контейнерам не нужны.
Порты PostgreSQL и backend опубликованы только на `127.0.0.1` хоста; не меняйте адрес на
`0.0.0.0` и не открывайте эти порты в firewall. Для работы бота нужны исходящие HTTPS-
подключения к Telegram и, если используется импорт BGG, к BoardGameGeek.

1. Установите Docker Engine и Compose plugin из официального репозитория для вашей ОС.
   Ограничьте SSH доступ доверенными IP-адресами и оставьте firewall закрытым для остальных
   входящих портов. Публичный HTTP(S)-reverse proxy для этого бота не требуется.
2. Клонируйте проект на сервер и создайте `.env` из шаблона. Замените все значения-заглушки:
   используйте токен Telegram из BotFather, а для `DB_PASSWORD` и `INTERNAL_API_TOKEN`
   сгенерируйте разные случайные секреты (например, `openssl rand -hex 32`). При включенном
   импорте BGG укажите действующий `BGG_ACCESS_TOKEN`.
3. Установите права на файл секретов и убедитесь, что он не попал в Git:

   ```sh
   chmod 600 .env
   git check-ignore .env
   ```

   Не публикуйте `.env` и не передавайте его в логи. Переменные окружения доступны
   администраторам Docker-хоста.
4. Проверьте конфигурацию и запустите весь стек:

   ```sh
   docker compose --env-file .env -f docker/docker-compose.yml config --quiet
   docker compose --env-file .env -f docker/docker-compose.yml up -d --build
   docker compose --env-file .env -f docker/docker-compose.yml ps
   ```

5. Если контейнер не стал `healthy`/`running`, изучите логи:

   ```sh
   docker compose --env-file .env -f docker/docker-compose.yml logs backend bot migrate
   ```

   Обновляйте приложение через `up -d --build`; для резервных копий регулярно сохраняйте
   PostgreSQL вне VPS. Команда `down` оставляет volume с данными; не используйте `down -v`,
   если не хотите удалить базу.

## Что будет следующим шагом

- SQLAlchemy-модели
- Alembic-миграции
- первая версия API
- затем сценарии бота
