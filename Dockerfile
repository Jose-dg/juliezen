FROM python:3.11-slim

# Buenas prácticas de runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# SO deps mínimas (psycopg/pillow). Evita postgresql-client si no lo usas.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
 && pip install -r requirements.txt

# Código
COPY . .

# Usuario no root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# EXPOSE es opcional en Render; se deja para documentación
EXPOSE 8000

# ¡IMPORTANTE! Escuchar en 0.0.0.0:$PORT
# Variables para tunear sin rebuild (workers/threads/timeout)
CMD gunicorn core.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-3} \
    --threads ${GTHREADS:-2} \
    --timeout ${TIMEOUT:-60} \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --access-logfile - --error-logfile - \
    --worker-tmp-dir /dev/shm