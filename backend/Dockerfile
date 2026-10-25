# --- Autos Colombia · API (FastAPI + PostgreSQL) ---
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

# Dependencias primero: cambian menos que el código y así se reutiliza la caché.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Solo lo necesario en runtime; las pruebas no viajan en la imagen.
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Render inyecta PORT (por defecto 10000); en docker-compose se fija en 8000.
# El contenedor debe escuchar en 0.0.0.0 para recibir peticiones.

# 1) Migraciones versionadas antes de aceptar tráfico.
# 2) uvicorn escucha en todas las interfaces, como exige el contenedor.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1}"]
