# checks.py
import aiohttp
import time
import socket
import redis.asyncio as aioredis
import asyncpg
import aio_pika


from config import (
    REDIS_URL,
    POSTGRES_DSN,
    RABBIT_HOST,
    RABBIT_PORT,
    RABBIT_USER,
    RABBIT_PASSWORD,
)

# 🔴 Redis
async def check_redis():
    r = None
    try:
        start = time.perf_counter()
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        await r.ping()
        rtt = (time.perf_counter() - start) * 1000
        return {"ok": True, "rtt": round(rtt, 2)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if r:
            await r.close()


# 🔵 PostgreSQL
async def check_postgres():
    conn = None
    try:
        start = time.perf_counter()
        conn = await asyncpg.connect(POSTGRES_DSN, timeout=2)
        await conn.execute("SELECT 1;")
        rtt = (time.perf_counter() - start) * 1000
        return {"ok": True, "rtt": round(rtt, 2)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if conn:
            await conn.close()


# 🟠 RabbitMQ
async def check_rabbitmq():
    connection = None
    try:
        start = time.perf_counter()
        connection = await aio_pika.connect_robust(
            host=RABBIT_HOST,
            port=RABBIT_PORT,
            login=RABBIT_USER,
            password=RABBIT_PASSWORD,
            timeout=2,
        )
        rtt = (time.perf_counter() - start) * 1000
        return {"ok": True, "rtt": round(rtt, 2)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if connection:
            await connection.close()


# 🟣 Qdrant
async def check_qdrant(session: aiohttp.ClientSession, url: str):
    try:
        start = time.perf_counter()
        async with session.get(f"{url}/readyz", timeout=2) as res:
            rtt = (time.perf_counter() - start) * 1000
            return {
                "ok": res.status == 200,   # ✅ SEULE CONDITION
                "status": res.status,
                "rtt": round(rtt, 2),
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# 🟡 MinIO
async def check_minio(session: aiohttp.ClientSession, url: str):
    if not url:
        return {"ok": False, "error": "MINIO_URL not configured"}

    try:
        start = time.perf_counter()
        async with session.get(f"{url}/minio/health/ready", timeout=2) as res:
            rtt = (time.perf_counter() - start) * 1000
            return {
                "ok": res.status == 200,
                "status": res.status,
                "rtt": round(rtt, 2),
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# 🌐 Microservices HTTP
async def check_http_service(name: str, url: str, session: aiohttp.ClientSession):
    try:
        start = time.perf_counter()
        async with session.get(url, timeout=2) as res:
            rtt = (time.perf_counter() - start) * 1000
            ok = res.status in (200, 204, 404)
            return {
                "ok": ok,
                "status": res.status,
                "rtt": round(rtt, 2),
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
        },
    }