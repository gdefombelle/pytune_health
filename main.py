from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import aiohttp
import asyncio
import time

from checks import (
    check_redis,
    check_postgres,
    check_http_service,
    check_system
)
from config import SERVICES

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # pour dev
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    started = time.perf_counter()

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
            # si exception => r est une Exception
            if isinstance(r, Exception):
                services_ok[name] = {"ok": False, "error": str(r)}
            else:
                services_ok[name] = r

    sys_info = check_system()

    # statut global
    global_status = "online"
    reason = "all_ok"

    # si un service HTTP est KO → degraded
    for name, r in services_ok.items():
        if not r.get("ok"):
            global_status = "degraded"
            reason = f"service_{name}_down"

    redis_ok = await redis_task
    postgres_ok = await postgres_task

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
        .page {
          width: 100%;
          max-width: 960px;
        }
        h1 {
          font-size: 1.9rem;
          margin: 0 0 .5rem;
        }
        .subtitle {
          opacity: .7;
          font-size: .9rem;
          margin-bottom: 1.5rem;
        }
        .card {
          background: radial-gradient(circle at top left, #18213a, #070916);
          border-radius: 16px;
          padding: 1.4rem 1.6rem;
          border: 1px solid rgba(255,255,255,.06);
          box-shadow: 0 18px 40px rgba(0,0,0,.45);
          margin-bottom: 1rem;
        }
        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 1rem;
          margin-bottom: .6rem;
        }
        .badge {
          display: inline-flex;
          align-items: center;
          gap: .4rem;
          padding: .25rem .7rem;
          border-radius: 999px;
          font-size: .78rem;
          letter-spacing: .02em;
          text-transform: uppercase;
          font-weight: 600;
        }
        .badge-dot {
          width: 8px;
          height: 8px;
          border-radius: 999px;
          background: currentColor;
        }
        .badge-online {
          color: #00e08a;
          background: rgba(0, 224, 138, 0.12);
        }
        .badge-degraded {
          color: #f7c948;
          background: rgba(247, 201, 72, 0.14);
        }
        .badge-offline {
          color: #ff6b81;
          background: rgba(255, 107, 129, 0.16);
        }
        .kpi-row {
          display: flex;
          flex-wrap: wrap;
          gap: .8rem;
          margin-top: .4rem;
        }
        .kpi {
          min-width: 120px;
          padding: .6rem .9rem;
          border-radius: 10px;
          background: rgba(0,0,0,0.25);
          border: 1px solid rgba(255,255,255,0.04);
          font-size: .8rem;
        }
        .kpi-label {
          opacity: .6;
          margin-bottom: .15rem;
        }
        .kpi-value {
          font-weight: 600;
          font-size: .95rem;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: .85rem;
        }
        th, td {
          padding: .45rem .3rem;
          text-align: left;
        }
        th {
          opacity: .6;
          font-weight: 500;
          border-bottom: 1px solid rgba(255,255,255,.08);
        }
        tr + tr td {
          border-top: 1px solid rgba(255,255,255,.04);
        }
        .service-name {
          font-weight: 500;
        }
        .status-chip {
          display: inline-flex;
          align-items: center;
          gap: .3rem;
          padding: .15rem .5rem;
          border-radius: 999px;
          font-size: .75rem;
        }
        .chip-ok {
          color: #00e08a;
          background: rgba(0,224,138,0.1);
        }
        .chip-fail {
          color: #ff6b81;
          background: rgba(255,107,129,0.1);
        }
        .mono {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
          font-size: .78rem;
        }
        .footer {
          margin-top: 1rem;
          opacity: .55;
          font-size: .75rem;
          text-align: right;
        }
        .pill {
          display: inline-flex;
          padding: .1rem .45rem;
          border-radius: 999px;
          border: 1px solid rgba(255,255,255,.1);
          margin-left: .25rem;
        }
        .warning {
          margin-top: .5rem;
          font-size: .78rem;
          opacity: .65;
        }
        @media (max-width: 640px) {
          .card-header {
            flex-direction: column;
            align-items: flex-start;
          }
          .footer {
            text-align: left;
          }
        }
      </style>
    </head>
    <body>
      <div class="page">
        <div class="card">
          <div class="card-header">
            <div>
              <h1>PyTune Platform – Status</h1>
              <div class="subtitle">
                Vue d'ensemble temps réel de l'infrastructure PyTune
              </div>
            </div>
            <div id="global-badge" class="badge badge-offline">
              <span class="badge-dot"></span>
              <span id="global-status-text">Unknown</span>
            </div>
          </div>

          <div class="kpi-row">
            <div class="kpi">
              <div class="kpi-label">État global</div>
              <div class="kpi-value" id="kpi-global">–</div>
            </div>
            <div class="kpi">
              <div class="kpi-label">Latence moyenne</div>
              <div class="kpi-value"><span id="kpi-rtt">–</span> ms</div>
            </div>
            <div class="kpi">
              <div class="kpi-label">Redis</div>
              <div class="kpi-value"><span id="kpi-redis">–</span></div>
            </div>
            <div class="kpi">
              <div class="kpi-label">PostgreSQL</div>
              <div class="kpi-value"><span id="kpi-postgres">–</span></div>
            </div>
            <div class="kpi">
              <div class="kpi-label">Load (1 / 5 / 15 min)</div>
              <div class="kpi-value mono" id="kpi-load">–</div>
            </div>
          </div>

          <div class="warning">
            Cette page interroge <span class="mono">/health</span> toutes les 10 secondes.
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div>
              <strong>Microservices</strong>
              <span class="subtitle">Détails par service (HTTP)</span>
            </div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Service</th>
                <th>Statut</th>
                <th>Code HTTP</th>
                <th>Latence (ms)</th>
              </tr>
            </thead>
            <tbody id="services-body">
              <tr><td colspan="4">Chargement...</td></tr>
            </tbody>
          </table>
        </div>

        <div class="footer">
          Mis à jour : <span id="last-update">–</span>
          <span class="pill mono">health.pytune.com</span>
        </div>
      </div>

      <script>
        function setGlobalBadge(status) {
          const el = document.getElementById('global-badge');
          const text = document.getElementById('global-status-text');
          el.classList.remove('badge-online', 'badge-degraded', 'badge-offline');
          if (status === 'online') {
            el.classList.add('badge-online');
            text.textContent = 'ONLINE';
          } else if (status === 'degraded') {
            el.classList.add('badge-degraded');
            text.textContent = 'DEGRADED';
          } else {
            el.classList.add('badge-offline');
            text.textContent = 'OFFLINE';
          }
        }

        function chip(ok) {
          const cls = ok ? 'chip-ok' : 'chip-fail';
          const label = ok ? 'OK' : 'Down';
          return '<span class="status-chip ' + cls + '"><span class="badge-dot"></span>' + label + '</span>';
        }

        async function refresh() {
          try {
            const res = await fetch('/health', { cache: 'no-store' });
            const data = await res.json();

            // Global
            setGlobalBadge(data.status);
            document.getElementById('kpi-global').textContent = data.status.toUpperCase();
            document.getElementById('kpi-rtt').textContent = (data.rtt ?? 0).toFixed(2);

            const redisText = data.redis?.ok ? 'OK (' + (data.redis.rtt ?? 0).toFixed(1) + ' ms)' : 'Down';
            const pgText = data.postgres?.ok ? 'OK (' + (data.postgres.rtt ?? 0).toFixed(1) + ' ms)' : 'Down';

            document.getElementById('kpi-redis').textContent = redisText;
            document.getElementById('kpi-postgres').textContent = pgText;

            const load = data.system?.load || {};
            document.getElementById('kpi-load').textContent =
              (load["1m"] ?? 0).toFixed(2) + ' / ' +
              (load["5m"] ?? 0).toFixed(2) + ' / ' +
              (load["15m"] ?? 0).toFixed(2);

            document.getElementById('last-update').textContent =
              new Date().toLocaleString();

            // Services
            const tbody = document.getElementById('services-body');
            tbody.innerHTML = '';

            const services = data.services || {};
            const names = Object.keys(services).sort();

            if (names.length === 0) {
              const tr = document.createElement('tr');
              const td = document.createElement('td');
              td.colSpan = 4;
              td.textContent = 'Aucun service configuré.';
              tr.appendChild(td);
              tbody.appendChild(tr);
            } else {
              for (const name of names) {
                const s = services[name];
                const tr = document.createElement('tr');

                const tdName = document.createElement('td');
                tdName.className = 'service-name';
                tdName.textContent = name;
                tr.appendChild(tdName);

                const tdStatus = document.createElement('td');
                tdStatus.innerHTML = chip(!!s.ok);
                tr.appendChild(tdStatus);

                const tdCode = document.createElement('td');
                tdCode.textContent = s.status ?? '—';
                tr.appendChild(tdCode);

                const tdRtt = document.createElement('td');
                tdRtt.textContent = s.rtt != null ? Number(s.rtt).toFixed(2) : '—';
                tr.appendChild(tdRtt);

                tbody.appendChild(tr);
              }
            }

          } catch (e) {
            console.error('Failed to load health', e);
            setGlobalBadge('offline');
            document.getElementById('kpi-global').textContent = 'ERROR';
            document.getElementById('kpi-rtt').textContent = '–';
            document.getElementById('services-body').innerHTML =
              '<tr><td colspan="4">Impossible de joindre /health</td></tr>';
          }
        }

        refresh();
        setInterval(refresh, 10000);
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)