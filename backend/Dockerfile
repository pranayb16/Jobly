FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

RUN groupadd --system jobly && useradd --system --gid jobly --create-home jobly

COPY pyproject.toml ./
COPY jobly ./jobly

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

USER jobly

CMD ["sh", "-c", "exec uvicorn jobly.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
