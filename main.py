from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import aiohttp
import asyncio
import time

from checks import (
    check_redis,
    check_postgres,
    check_rabbitmq,
    check_qdrant,
    check_minio,
    check_http_service,
    check_system,
    check_ollama,
)
from checks_workers import check_email_worker,check_piano_worker

from config import (
    SERVICES,
    QDRANT_URL,
    MINIO_URL,
    OLLAMA_URL,
)

app = FastAPI(title="PyTune Health Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATUS_HTML = Path("templates/status.html").read_text(encoding="utf-8")

# -------------------------------------------------------------------
# HEALTH API
# -------------------------------------------------------------------
@app.get("/health")
async def health():
    started = time.perf_counter()

    async with aiohttp.ClientSession() as session:
        # ---- HTTP microservices ----
        service_checks = {
            name: check_http_service(name, url, session)
            for name, url in SERVICES.items()
        }

        service_results = await asyncio.gather(
            *service_checks.values(),
            return_exceptions=True,
        )

        services_ok: dict[str, dict] = {}
        for (name, _), result in zip(service_checks.items(), service_results):
            if isinstance(result, Exception):
                services_ok[name] = {"ok": False, "error": str(result)}
            else:
                services_ok[name] = result

        # ---- Infra HTTP externes ----
        qdrant_task = check_qdrant(session, QDRANT_URL)
        minio_task = check_minio(session, MINIO_URL)
        ollama_task = check_ollama(session, OLLAMA_URL)

        qdrant_ok, minio_ok, ollama_ok = await asyncio.gather(
            qdrant_task,
            minio_task,
            ollama_task,
        )

        # ---- Workers (indirect / tri-state) ----

        email_worker_task = asyncio.to_thread(check_email_worker)
        piano_worker_task = asyncio.to_thread(check_piano_worker)
        email_worker_ok, piano_worker_ok = await asyncio.gather(
            email_worker_task,
            piano_worker_task,
        )

    # ---- Infra core ----
    redis_ok, postgres_ok, rabbit_ok = await asyncio.gather(
        check_redis(),
        check_postgres(),
        check_rabbitmq(),
    )

    sys_info = check_system()

    # ----------------------------------------------------------------
    # GLOBAL STATUS LOGIC
    # ----------------------------------------------------------------
    global_status = "online"
    reason = "all_ok"

    # HTTP services
    for name, r in services_ok.items():
        if not r.get("ok"):
            global_status = "degraded"
            reason = f"service_{name}_down"
            break

    # Infra secondaires
    if not rabbit_ok.get("ok"):
        global_status = "degraded"
        reason = "rabbitmq_down"

    if not qdrant_ok.get("ok"):
        global_status = "degraded"
        reason = "qdrant_down"

    if not minio_ok.get("ok"):
        global_status = "degraded"
        reason = "minio_down"

    if ollama_ok.get("ok") is False:
        global_status = "degraded"
        reason = "ollama_down"

    # Infra critiques
    if not redis_ok.get("ok"):
        global_status = "offline"
        reason = "redis_down"

    if not postgres_ok.get("ok"):
        global_status = "offline"
        reason = "postgres_down"

    # Workers → ne dégradent QUE si explicitement false
    if email_worker_ok.get("ok") is False:
        global_status = "degraded"
        reason = "email_worker_down"

    total_rtt = (time.perf_counter() - started) * 1000

    return {
        "status": global_status,
        "ok": global_status == "online",
        "degraded": global_status == "degraded",
        "reason": reason,
        "rtt": round(total_rtt, 2),
        "target": "pytune_platform",

        "redis": redis_ok,
        "postgres": postgres_ok,
        "rabbitmq": rabbit_ok,
        "qdrant": qdrant_ok,
        "minio": minio_ok,
        "ollama": ollama_ok,

        "services": services_ok,
        "workers": {
            "email_worker": email_worker_ok,
            "piano_worker": piano_worker_ok,
        },
        "system": sys_info,
    }


# -------------------------------------------------------------------
# STATUS PAGE (HTML)
# -------------------------------------------------------------------
@app.get("/status", response_class=HTMLResponse)
async def status_page():
  return HTMLResponse(content=STATUS_HTML)