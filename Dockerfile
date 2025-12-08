FROM python:3.12-slim

WORKDIR /app

# dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Installer les deps Python
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    aiohttp \
    asyncpg \
    "redis[hiredis]" \
    python-dotenv

# Copier le code
COPY . .

# On dit au code qu'on est dans Docker
ENV DOCKERIZED=1

# Port interne
EXPOSE 8010

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]