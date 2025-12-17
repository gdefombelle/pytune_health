import os
from urllib.parse import quote_plus

# ---------- Redis ----------
REDIS_HOST = os.getenv("REDIS_HOST", "pytune-redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

REDIS_URL = os.getenv("REDIS_URL") or (
    f"redis://:{quote_plus(REDIS_PASSWORD)}@{REDIS_HOST}:{REDIS_PORT}"
    if REDIS_PASSWORD
    else f"redis://{REDIS_HOST}:{REDIS_PORT}"
)

# ---------- Postgres ----------
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("FASTAPI_USER", "fastapi_user")
DB_PASSWORD = os.getenv("FASTAPI_PWD", "changeme")
DB_NAME = os.getenv("DB_NAME", "pianos")

POSTGRES_DSN = (
    f"postgres://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ---------- RabbitMQ ----------
# RabbitMQ
RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
RABBIT_PORT = int(os.getenv("RABBIT_PORT", "5672"))
RABBIT_USER = os.getenv("RABBIT_USER", "admin")
RABBIT_PASSWORD = os.getenv("RABBIT_PASSWORD", "MyStr0ngP@ss2024!")


# ---------- Qdrant ----------
QDRANT_URL = os.getenv("QDRANT_URL","http://195.201.9.184:6333") 

# ---------- MinIO ----------
MINIO_HOST = os.getenv("MINIO_HOST", "minio")
MINIO_PORT = int(os.getenv("MINIO_PORT", "9000"))
MINIO_URL = os.getenv("MINIO_URL") or f"http://{MINIO_HOST}:{MINIO_PORT}"


# --------- OLLAMA ------------
OLLAMA_URL = os.getenv("OLLAMA_URL")  # pas de default

# ---------- Mode Docker ou pas ----------
DOCKERIZED = os.getenv("DOCKERIZED", "0") == "1"

if DOCKERIZED:
    # ➜ on parle directement aux containers dans le réseau Docker
    SERVICES = {
        "oauth":  "http://pytune_oauth:8000",
        "ai_router": "http://pytune_ai_router:8006",
        "piano":  "http://pytune_piano:8001",
        "user":   "http://pytune_user:8002",
        "admin":  "http://pytune_admin:8003",
        "stream": "http://pytune_stream:8009",
        "diagnosis": "http://pytune_diagnosis:8008",
        "storage":   "http://pytune_storage:8005",
        "llm_proxy": "http://pytune_llm_proxy:8007",
        "pkce": "http://pytune_pkce:8004",
        "web":       "http://pytune_web:3000",
    }
else:
    # ➜ fallback : URLs publiques (tests depuis ton Mac, etc.)
    SERVICES = {
        "oauth": os.getenv("SERVICE_OAUTH_URL",      "https://oauth.pytune.com"),
        "ai_router": os.getenv("SERVICE_AI_ROUTER_URL", "https://ai-router.pytune.com"),
        "piano": os.getenv("SERVICE_PIANO_URL",      "https://pianos.pytune.com"),
        "user": os.getenv("SERVICE_USER_URL",        "https://user.pytune.com"),
        "admin": os.getenv("SERVICE_ADMIN_URL",      "https://admin.pytune.com"),
        "stream": os.getenv("SERVICE_STREAM_URL",    "https://stream.pytune.com"),
        "diagnosis": os.getenv("SERVICE_DIAG_URL",   "https://diagnosis.pytune.com"),
        "storage": os.getenv("SERVICE_STORAGE_URL",  "https://storage.pytune.com"),
        "llm_proxy": os.getenv("SERVICE_LLM_URL",    "https://llm.pytune.com"),
        "pkce": os.getenv("SERVICE_LLM_URL",    "https://pkce.pytune.com"),
        "web": os.getenv("SERVICE_WEB_URL",          "https://pytune.com"),
    }