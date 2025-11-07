# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /auth
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install psql client for running manual SQL migrations from this container
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy application and Alembic migration assets
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
# Copy manual SQL migrations into image at /auth/migrations
COPY migrations ./migrations
EXPOSE 8000
CMD ["python", "-m", "app.start"]
