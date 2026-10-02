FROM python:3.12-slim AS base

WORKDIR /app

# System deps needed by psycopg2 (not -binary... wait, we use psycopg2-binary,
# which ships its own libpq — no build-essential/libpq-dev needed here).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Runs migrations before starting so a fresh `docker compose up` always has
# an up-to-date schema — see docker-compose.yml for how `worker` overrides
# this CMD to run Celery instead against the same image.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
