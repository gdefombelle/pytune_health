from fastapi import FastAPI
import aiohttp
import asyncio

from checks import (
    check_redis,
    check_postgres,
    check_http_service,
    check_system
)
from config import SERVICES

app = FastAPI()

@app.get("/health")
async def health():
    async with aiohttp.ClientSession() as session:
        service_checks = {
            name: check_http_service(name, url, session)
            for name, url in SERVICES.items()
        }

        redis_task = check_redis()
        postgres_task = check_postgres()

        service_results = await asyncio.gather(
            *service_checks.values(), return_exceptions=True
        )

        services_ok = {}
        for (name, _), r in zip(service_checks.items(), service_results):
            services_ok[name] = r

    sys_info = check_system()

    global_status = "online"

    # degraded si un service ne répond pas bien
    for name, r in services_ok.items():
        if not r["ok"]:
            global_status = "degraded"

    redis_ok = await redis_task
    postgres_ok = await postgres_task

    # offline si infra down
    if not redis_ok["ok"] or not postgres_ok["ok"]:
        global_status = "offline"

    return {
        "status": global_status,
        "redis": redis_ok,
        "postgres": postgres_ok,
        "services": services_ok,
        "system": sys_info
    }