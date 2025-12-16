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
)

from config import (
    SERVICES,
    QDRANT_URL,
    MINIO_URL,
)

app = FastAPI(title="PyTune Health Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # health endpoint public
    allow_methods=["*"],
    allow_headers=["*"],
)


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

        # ---- Infra externes HTTP ----
        qdrant_task = check_qdrant(session, QDRANT_URL)
        minio_task = check_minio(session, MINIO_URL)

        qdrant_ok, minio_ok = await asyncio.gather(
            qdrant_task,
            minio_task,
        )

    # ---- Infra core ----
    redis_task = check_redis()
    postgres_task = check_postgres()
    rabbit_task = check_rabbitmq()

    redis_ok, postgres_ok, rabbit_ok = await asyncio.gather(
        redis_task,
        postgres_task,
        rabbit_task,
    )

    sys_info = check_system()

    # ---- Global status logic ----
    global_status = "online"
    reason = "all_ok"

    # HTTP services → degraded
    for name, r in services_ok.items():
        if not r.get("ok"):
            global_status = "degraded"
            reason = f"service_{name}_down"
            break

    # Infra secondaires → degraded
    if not rabbit_ok.get("ok"):
        global_status = "degraded"
        reason = "rabbitmq_down"

    if not qdrant_ok.get("ok"):
        global_status = "degraded"
        reason = "qdrant_down"

    if not minio_ok.get("ok"):
        global_status = "degraded"
        reason = "minio_down"

    # Infra critiques → offline
    if not redis_ok.get("ok"):
        global_status = "offline"
        reason = "redis_down"

    if not postgres_ok.get("ok"):
        global_status = "offline"
        reason = "postgres_down"

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

        "services": services_ok,
        "system": sys_info,
    }


@app.get("/status", response_class=HTMLResponse)
async def status_page():
    html = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>PyTune Platform – Status</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color-scheme: dark;
    }
    body {
      margin: 0;
      padding: 2rem 1rem;
      background: #050712;
      color: #e5ecff;
      display: flex;
      justify-content: center;
    }
    .page { width: 100%; max-width: 960px; }
    h1 { font-size: 1.9rem; margin: 0 0 .5rem; }
    .subtitle { opacity: .7; font-size: .9rem; margin-bottom: 1.5rem; }
    .card {
      background: radial-gradient(circle at top left, #18213a, #070916);
      border-radius: 16px;
      padding: 1.4rem 1.6rem;
      border: 1px solid rgba(255,255,255,.06);
      box-shadow: 0 18px 40px rgba(0,0,0,.45);
      margin-bottom: 1rem;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: .4rem;
      padding: .25rem .7rem;
      border-radius: 999px;
      font-size: .78rem;
      font-weight: 600;
      text-transform: uppercase;
    }
    .badge-online { color: #00e08a; background: rgba(0,224,138,.12); }
    .badge-degraded { color: #f7c948; background: rgba(247,201,72,.14); }
    .badge-offline { color: #ff6b81; background: rgba(255,107,129,.16); }
    .badge-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }

    .kpi-row { display: flex; flex-wrap: wrap; gap: .8rem; margin-top: .6rem; }
    .kpi {
      min-width: 130px;
      padding: .6rem .9rem;
      border-radius: 10px;
      background: rgba(0,0,0,.25);
      font-size: .8rem;
    }
    .kpi-ok-bg {
      background: rgba(0,224,138,.12);
    }
    .kpi-down-bg {
      background: rgba(255,107,129,.16);
    }
    .kpi-ok {
      color: #00e08a;
    }

    .kpi-down {
      color: #ff6b81;
    }
    table { width: 100%; border-collapse: collapse; font-size: .85rem; }
    th, td { padding: .45rem .3rem; text-align: left; }
    th { opacity: .6; border-bottom: 1px solid rgba(255,255,255,.08); }
    tr + tr td { border-top: 1px solid rgba(255,255,255,.04); }
    .status-chip {
      display: inline-flex;
      align-items: center;
      gap: .3rem;
      padding: .15rem .5rem;
      border-radius: 999px;
      font-size: .75rem;
    }
    .chip-ok { color: #00e08a; background: rgba(0,224,138,.1); }
    .chip-fail { color: #ff6b81; background: rgba(255,107,129,.1); }
    .footer { margin-top: 1rem; opacity: .55; font-size: .75rem; text-align: right; }
  </style>
</head>
<body>
<div class="page">
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <div>
        <h1>PyTune Platform – Status</h1>
        <div class="subtitle">Infrastructure temps réel</div>
      </div>
      <div id="global-badge" class="badge badge-offline">
        <span class="badge-dot"></span>
        <span id="global-status-text">UNKNOWN</span>
      </div>
    </div>

    <div class="kpi-row">
      <div class="kpi">Global<br><b id="kpi-global">–</b></div>
      <div class="kpi">RTT<br><b><span id="kpi-rtt">–</span> ms</b></div>
      <div class="kpi">Redis<br><b id="kpi-redis">–</b></div>
      <div class="kpi">Postgres<br><b id="kpi-postgres">–</b></div>
      <div class="kpi">RabbitMQ<br><b id="kpi-rabbit">–</b></div>
      <div class="kpi">Qdrant<br><b id="kpi-qdrant">–</b></div>
      <div class="kpi">MinIO<br><b id="kpi-minio">–</b></div>
    </div>
  </div>

  <div class="card">
    <table>
      <thead><tr><th>Service</th><th>Status</th><th>HTTP</th><th>RTT (ms)</th></tr></thead>
      <tbody id="services-body"><tr><td colspan="4">Loading…</td></tr></tbody>
    </table>
  </div>

  <div class="footer">health.pytune.com</div>
</div>

<script>
function setGlobal(status) {
  const b = document.getElementById('global-badge');
  const t = document.getElementById('global-status-text');
  b.className = 'badge badge-' + status;
  t.textContent = status.toUpperCase();
}

function chip(ok) {
  return '<span class="status-chip ' + (ok ? 'chip-ok' : 'chip-fail') + '">' +
         '<span class="badge-dot"></span>' + (ok ? 'OK' : 'DOWN') + '</span>';
}
function setInfra(id, ok) {
  const el = document.getElementById(id);
  const card = el.closest('.kpi');

  el.textContent = ok ? 'OK' : 'Down';
  el.className = ok ? 'kpi-ok' : 'kpi-down';

  card.classList.remove('kpi-ok-bg', 'kpi-down-bg');
  card.classList.add(ok ? 'kpi-ok-bg' : 'kpi-down-bg');
}

async function refresh() {
  const r = await fetch('/health', { cache: 'no-store' });
  const d = await r.json();

  setGlobal(d.status);
  document.getElementById('kpi-global').textContent = d.status.toUpperCase();
  document.getElementById('kpi-rtt').textContent = d.rtt.toFixed(2);

  setInfra('kpi-redis', d.redis.ok);
  setInfra('kpi-postgres', d.postgres.ok);
  setInfra('kpi-rabbit', d.rabbitmq.ok);
  setInfra('kpi-qdrant', d.qdrant?.ok);
  setInfra('kpi-minio', d.minio?.ok);

  const tbody = document.getElementById('services-body');
  tbody.innerHTML = '';
  for (const [name, s] of Object.entries(d.services)) {
    tbody.innerHTML +=
      `<tr><td>${name}</td><td>${chip(s.ok)}</td><td>${s.status ?? '–'}</td><td>${s.rtt ?? '–'}</td></tr>`;
  }
}

refresh();
setInterval(refresh, 10000);
</script>
</body>
</html>
"""
    return HTMLResponse(content=html)