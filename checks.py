import aiohttp
import asyncio
import socket
import time
import redis.asyncio as aioredis
import asyncpg


# -----------------------------
# 🔴 Redis
# -----------------------------
async def check_redis():
    try:
        r = aioredis.from_url("redis://redis:6379", decode_responses=True)
        start = time.perf_counter()
        await r.ping()
        rtt = (time.perf_counter() - start) * 1000
        return {"ok": True, "rtt": round(rtt, 2)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# -----------------------------
# 🔵 PostgreSQL
# -----------------------------
async def check_postgres():
    try:
        start = time.perf_counter()
        conn = await asyncpg.connect(
            user="postgres",
            password="postgres",
            host="postgres",
            port=5432,
            database="pytune"
        )
        await conn.execute("SELECT 1;")
        await conn.close()
        rtt = (time.perf_counter() - start) * 1000
        return {"ok": True, "rtt": round(rtt, 2)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# -----------------------------
# 🌐 Microservices HTTP
# -----------------------------
async def check_http_service(name: str, url: str, session: aiohttp.ClientSession):
    try:
        start = time.perf_counter()
        async with session.get(url, timeout=2) as res:
            rtt = (time.perf_counter() - start) * 1000
            ok = res.status in (200, 204)
            return {
                "ok": ok,
                "status": res.status,
                "rtt": round(rtt, 2)
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# -----------------------------
# 🖥️ System info (local container)
# -----------------------------
def check_system():
    load1, load5, load15 = (0, 0, 0)
    try:
        import os
        load1, load5, load15 = os.getloadavg()
    except:
        pass

    return {
        "hostname": socket.gethostname(),
        "load": {
            "1m": round(load1, 2),
            "5m": round(load5, 2),
            "15m": round(load15, 2),
        }
    }