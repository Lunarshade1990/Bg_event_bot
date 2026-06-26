FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN python -m pip install --no-cache-dir --upgrade pip

RUN apt-get update \
	&& apt-get install -y --no-install-recommends postgresql-client \
	&& rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md alembic.ini ./
COPY backend ./backend
COPY bot ./bot
COPY docker/wait-for-postgres.sh /usr/local/bin/wait-for-postgres

RUN chmod +x /usr/local/bin/wait-for-postgres
RUN chmod -R a+rX /app

RUN python -m pip install --no-cache-dir .

RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

CMD ["python", "-m", "bot.app.main"]
