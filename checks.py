# checks.py
import aiohttp
import time
import socket
import redis.asyncio as aioredis
import asyncpg

from config import REDIS_URL, POSTGRES_DSN


# 🔴 Redis
async def check_redis():
    try:
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        start = time.perf_counter()
        await r.ping()
        rtt = (time.perf_counter() - start) * 1000
        return {"ok": True, "rtt": round(rtt, 2)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# 🔵 PostgreSQL
async def check_postgres():
    try:
        start = time.perf_counter()
        conn = await asyncpg.connect(POSTGRES_DSN)
        await conn.execute("SELECT 1;")
        await conn.close()
        rtt = (time.perf_counter() - start) * 1000
        return {"ok": True, "rtt": round(rtt, 2)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# 🌐 Microservices HTTP
async def check_http_service(name: str, url: str, session: aiohttp.ClientSession):
    try:
        start = time.perf_counter()
        async with session.get(url, timeout=2) as res:
            rtt = (time.perf_counter() - start) * 1000
            ok = res.status in (200, 204, 404)  # 404 JSON FastAPI peut compter comme "up"
            return {
                "ok": ok,
                "status": res.status,
                "rtt": round(rtt, 2)
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# 🖥️ System info
def check_system():
    load1 = load5 = load15 = 0.0
    try:
        import os
        load1, load5, load15 = os.getloadavg()
    except Exception:
        pass

    return {
        "hostname": socket.gethostname(),
        "load": {
            "1m": round(load1, 2),
            "5m": round(load5, 2),
            "15m": round(load15, 2),
        }
    }