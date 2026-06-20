# 📖 Cyberguard — Complete Guide

> Everything you need to know about setting up, connecting to, and using every feature of the Cyberguard platform.

---

## Table of Contents

1. [What is Cyberguard?](#what-is-cyberguard)
2. [System Architecture](#system-architecture)
3. [Prerequisites & Setup](#prerequisites--setup)
4. [Environment Variables (.env)](#environment-variables)
5. [Running the Application](#running-the-application)
6. [All API Endpoints](#all-api-endpoints)
   - [Core Simulation & Logs](#1-core-simulation--logs)
   - [Reports](#2-reports)
   - [LLM & Anomaly Detection](#3-llm--anomaly-detection)
   - [Live Streaming (SSE)](#4-live-streaming-sse)
   - [Auto-Response Engine](#5-auto-response-engine)
   - [Threshold Engine & Alerts](#6-threshold-engine--alerts)
   - [SMTP Email Alerting](#7-smtp-email-alerting)
   - [Port Scanner](#8-port-scanner)
7. [Frontend Pages & Navigation](#frontend-pages--navigation)
8. [How to Connect (Frontend ↔ Backend)](#how-to-connect)
9. [Step-by-Step Usage Guide](#step-by-step-usage-guide)
10. [Real-Time Monitoring Setup](#real-time-monitoring-setup)
11. [Gmail Email Alerts Setup](#gmail-email-alerts-setup)
12. [Ollama Local LLM Setup](#ollama-local-llm-setup)
13. [Background Services](#background-services)
14. [Troubleshooting](#troubleshooting)

---

## What is Cyberguard?

Cyberguard is an **AI-powered Security Operations Center (SOC)** platform with two major capabilities:

1. **AI Agent Pipeline** — 6 CrewAI agents (SENTRY → HUNTER → DETECTIVE → JUDGE → MEDIC → SCRIBE) that analyze security logs, detect attacks, score risks, generate firewall rules, and write incident reports.

2. **Real-Time Threat Monitoring** — A live log watcher that monitors system logs (auth.log, UFW, nginx, audit, etc.), runs threshold-based alerting, sends email notifications, scans for open ports, and streams everything to the browser via Server-Sent Events (SSE).

---

## System Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + Vite)                       │
│  Dashboard │ Live Monitor │ Investigation │ Report │ About        │
│  http://localhost:5173                                            │
└──────────────────┬────────────────────────────────────────────────┘
                   │  HTTP REST + SSE (Server-Sent Events)
                   ▼
┌───────────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI + Python)                        │
│  server.py → uvicorn → http://localhost:8000                      │
│                                                                   │
│  22 API Endpoints (see full list below)                           │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │  Log Watcher     │  │  Threshold Engine │  │  Alert Mailer   │  │
│  │  (watchdog)      │→ │  (11 rules)       │→ │  (Gmail SMTP)   │  │
│  └─────────────────┘  └──────────────────┘  └─────────────────┘  │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │  Anomaly Detect  │  │  Auto Responder   │  │  Port Scanner   │  │
│  │  (IsolationForest)│  │  (iptables)       │  │  (nmap)         │  │
│  └─────────────────┘  └──────────────────┘  └─────────────────┘  │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────┐                       │
│  │  Redis Pipeline  │  │  CrewAI Pipeline  │                      │
│  │  (optional)      │  │  (6 agents)       │                      │
│  └─────────────────┘  └──────────────────┘                       │
└───────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites & Setup

### What You Need

| Requirement | Version | How to Get It |
|---|---|---|
| **Python** | ≥ 3.10, < 3.14 | [python.org](https://python.org) |
| **Node.js** | ≥ 18.x | [nodejs.org](https://nodejs.org) |
| **UV** (Python pkg mgr) | latest | `pip install uv` |
| **Groq API Key** | required for AI agents | [console.groq.com](https://console.groq.com) |
| **Redis** | via docker-compose | `docker compose up -d` (included in project) |
| **nmap** | optional (for port scanning) | `sudo apt install nmap` |
| **Ollama** | optional (for local LLM) | [ollama.ai](https://ollama.ai) |

### Installation Steps

```bash
# 1. Clone / navigate to the project
cd KLH_hackathon

# 2. Backend setup
cd backend
pip install uv          # if not already installed
uv sync                 # installs all Python dependencies from pyproject.toml

# 3. Generate sample logs (first time)
uv run python generate_chaos_logs.py

# 4. Frontend setup
cd ../frontend
npm install
```

---

## Environment Variables

All configuration lives in `backend/.env`. Here's every variable:

### Required

| Variable | Description | Example |
|---|---|---|
| `GROQ_API_KEY` | Groq API key for LLaMA 3.3 70B | `gsk_abc123...` |

### Optional — Threat Intelligence

| Variable | Description | Default |
|---|---|---|
| `ABUSEIPDB_API_KEY` | AbuseIPDB reputation lookups | *(skipped if missing)* |
| `VIRUSTOTAL_API_KEY` | VirusTotal malware checks | *(skipped if missing)* |

### Optional — LLM Backend

| Variable | Description | Default |
|---|---|---|
| `LLM_BACKEND` | `groq` (cloud) or `ollama` (local) | `groq` |
| `OLLAMA_MODEL` | Ollama model to use | `deepseek-r1:1.5b` |
| `MODEL` | Groq model name | `groq/llama-3.3-70b-versatile` |

### Optional — Log Watcher

| Variable | Description | Default |
|---|---|---|
| `WATCH_LOG_PATH` | Custom log file to watch (if system logs inaccessible) | *(auto-detected)* |

### Optional — Auto-Response

| Variable | Description | Default |
|---|---|---|
| `AUTO_RESPOND_DRY_RUN` | `true` = log commands only, `false` = execute iptables | `true` |

### Optional — SMTP Email Alerts

| Variable | Description | Default |
|---|---|---|
| `SMTP_ENABLED` | Enable email alerting | `false` |
| `SMTP_HOST` | SMTP server host | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port (587=STARTTLS, 465=SSL) | `587` |
| `SMTP_USER` | Sender email address | *(required if enabled)* |
| `SMTP_PASSWORD` | Gmail App Password (NOT account password) | *(required if enabled)* |
| `ALERT_EMAIL_TO` | Recipient email(s), comma-separated | *(required if enabled)* |
| `ALERT_MIN_SEVERITY` | Minimum severity to email: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | `HIGH` |
| `ALERT_COOLDOWN_MINUTES` | Don't re-email same IP within N minutes | `5` |

### System Variables (don't change)

| Variable | Description |
|---|---|
| `LITELLM_LOG=ERROR` | Suppress LiteLLM debug noise |
| `CREWAI_TELEMETRY_OPT_OUT=true` | Disable CrewAI telemetry |
| `DISABLE_TELEMETRY=true` | Disable all telemetry |

---

## Running the Application

### Step 0 — Start Redis

```bash
# From the project root
docker compose up -d
```

Open **two terminals**:

### Terminal 1 — Backend (FastAPI)

```bash
cd backend
uv run uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

- ✅ API ready at: **http://localhost:8000**
- 📖 Swagger docs at: **http://localhost:8000/docs**
- On startup, the log watcher + port scanner + Redis connection start automatically

### Terminal 2 — Frontend (React)

```bash
cd frontend
npm run dev
```

- ✅ Dashboard at: **http://localhost:5173**

---

## All API Endpoints

The backend exposes **22 endpoints** organized into 8 groups. All are served at `http://localhost:8000`.

---

### 1. Core Simulation & Logs

These are the original endpoints that power the CrewAI agent pipeline.

#### `POST /run-simulation`

Triggers the full 6-agent analysis pipeline in the background.

```bash
curl -X POST http://localhost:8000/run-simulation
```

**Response:**
```json
{ "accepted": true }
```

**What happens:**
1. Anomaly detection runs on current CSV logs (IsolationForest)
2. Anomalous IPs are injected into the SENTRY agent's context
3. 6 CrewAI agents run sequentially (takes 3–10 minutes)
4. Auto-response engine runs on the generated report
5. Status returns to `idle` when complete

---

#### `GET /status`

Check if the pipeline is running or idle.

```bash
curl http://localhost:8000/status
```

**Response:**
```json
{ "status": "running" }
```
or
```json
{ "status": "idle" }
```

---

#### `GET /logs`

Returns raw CSV contents of the current security logs.

```bash
curl http://localhost:8000/logs
```

**Response:** Plain text CSV:
```
timestamp,ip_address,user,status,endpoint
2026-03-14T09:00:01,192.168.1.55,admin,Failed_Login,/ssh
...
```

---

#### `POST /upload-logs`

Upload a custom CSV file to analyze.

```bash
curl -X POST http://localhost:8000/upload-logs \
  -F "file=@my_logs.csv"
```

**CSV Format Required:**
```csv
timestamp,ip_address,user,status,endpoint
2026-03-14T09:00:01,10.0.0.1,admin,Failed_Login,/ssh
```

**Response:**
```json
{ "accepted": true }
```

The file is saved as `backend/data/simulation_logs.csv` and analysis starts automatically.

---

### 2. Reports

#### `GET /report`

Returns the raw Markdown incident report generated by the SCRIBE agent.

```bash
curl http://localhost:8000/report
```

**Response:** Full Markdown text of `incident_report.md`

---

#### `GET /report/raw`

Alias for `/report`. Returns the same raw Markdown content.

---

#### `GET /report/structured`

Parses the Markdown report and returns structured JSON.

```bash
curl http://localhost:8000/report/structured
```

**Response:**
```json
{
  "incident_id": "INC-2026-0314",
  "timestamps": {
    "created": "2026-03-14T09:00:00",
    "updated": null
  },
  "attack_type": "Coordinated Multi-Vector Attack",
  "risk_score": "92",
  "severity": "CRITICAL",
  "source_ip": "192.168.1.55",
  "targeted_service": "/api/admin",
  "evidence": "30 failed SSH logins in 30 seconds...",
  "recommended_actions": [
    "Block IP 192.168.1.55 at firewall",
    "Reset admin account credentials",
    "Enable MFA on all SSH accounts"
  ],
  "agent_notes": [
    { "agent": "SENTRY", "note": "Detected brute force from 192.168.1.55" },
    { "agent": "HUNTER", "note": "IP flagged by AbuseIPDB (confidence: 87%)" }
  ],
  "timeline": [
    { "time": "09:00:01", "event": "First failed login from 192.168.1.55" },
    { "time": "09:00:30", "event": "30th failed login — brute force confirmed" }
  ]
}
```

---

### 3. LLM & Anomaly Detection

#### `GET /llm-status`

Check which LLM backend is active and whether Ollama is reachable.

```bash
curl http://localhost:8000/llm-status
```

**Response:**
```json
{
  "backend": "groq",
  "model": "groq/llama-3.3-70b-versatile",
  "ollama_available": false
}
```

---

#### `GET /anomaly-report`

Returns the ML anomaly detection summary (IsolationForest results).

```bash
curl http://localhost:8000/anomaly-report
```

**Response:**
```json
{
  "anomalous_count": 3,
  "anomalous_ips": ["192.168.1.55", "45.33.22.11", "203.0.113.8"]
}
```

> **Note:** This runs on the current `simulation_logs.csv`. It's also automatically invoked before the CrewAI pipeline.

---

### 4. Live Streaming (SSE)

These endpoints use **Server-Sent Events** for real-time browser streaming.

#### `GET /stream`

Live stream of log events. Connect from a browser using `EventSource`:

```javascript
const es = new EventSource("http://localhost:8000/stream");
es.onmessage = (event) => {
  const parsed = JSON.parse(event.data);
  console.log(parsed);
  // { "type": "log", "data": { "timestamp": "...", "ip_address": "...", ... }, "id": 42 }
};
```

**Test from terminal:**
```bash
curl -N http://localhost:8000/stream
```

Each event is JSON:
```json
{
  "type": "log",
  "data": {
    "timestamp": "2026-03-14T09:26:01",
    "ip_address": "192.168.1.55",
    "user": "admin",
    "status": "Failed_Login",
    "endpoint": "/ssh",
    "source_log": "auth.log",
    "country": "Private/LAN",
    "city": "Private/LAN",
    "id": 42
  },
  "id": 42
}
```

**Features:**
- Auto-reconnect with `retry: 3000` (3 seconds)
- Keepalive comments every 30 seconds to prevent timeout
- Events include incremental IDs for ordering

---

#### `GET /stream/replay?limit=100`

Returns the last N events as a burst of SSE messages. Useful for catch-up after reconnection.

```bash
curl -N "http://localhost:8000/stream/replay?limit=50"
```

**Parameters:**
- `limit` (int, default 100, max 10000) — number of events to replay

---

#### `GET /alerts/live`

Live stream of threshold alerts. Fires only when a threshold is breached.

```javascript
const alertEs = new EventSource("http://localhost:8000/alerts/live");
alertEs.addEventListener("alert", (event) => {
  const alert = JSON.parse(event.data);
  console.log(alert);
  // { "id": "uuid", "severity": "HIGH", "ip_address": "...", ... }
});
```

Each alert event:
```json
{
  "id": "a1b2c3d4-...",
  "timestamp": "2026-03-14T09:26:15",
  "threshold_name": "failed_login_per_ip_per_minute",
  "current_value": 8,
  "threshold_value": 5,
  "severity": "HIGH",
  "ip_address": "192.168.1.55",
  "description": "8 failed logins from 192.168.1.55 in last minute",
  "auto_blocked": false
}
```

---

### 5. Auto-Response Engine

#### `POST /auto-respond`

Manually trigger the auto-response engine on the latest report.

```bash
# Dry run (default) — logs iptables commands but doesn't execute
curl -X POST http://localhost:8000/auto-respond \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# Live mode (CAUTION) — actually executes iptables on Linux
curl -X POST http://localhost:8000/auto-respond \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

**Response:**
```json
{
  "actions": [
    {
      "timestamp": "2026-03-14T09:26:15",
      "ip": "192.168.1.55",
      "action": "iptables -A INPUT -s 192.168.1.55 -j DROP",
      "dry_run": true,
      "executed": false
    }
  ]
}
```

---

#### `GET /response-audit`

Returns the full audit log of all auto-response actions.

```bash
curl http://localhost:8000/response-audit
```

**Response:** Array of action entries from `backend/data/response_audit.json`

---

### 6. Threshold Engine & Alerts

#### `GET /thresholds`

Returns the current threshold configuration.

```bash
curl http://localhost:8000/thresholds
```

**Response:**
```json
{
  "failed_login_per_ip_per_minute": 5,
  "sudo_escalation_per_hour": 3,
  "new_ssh_key_per_day": 1,
  "blocked_connections_per_ip_per_minute": 10,
  "unique_ports_scanned_per_ip": 5,
  "sqli_attempts_per_ip": 1,
  "http_4xx_per_ip_per_minute": 20,
  "http_5xx_per_minute": 10,
  "rogue_device_count": 1,
  "dns_anomaly_per_hour": 5,
  "same_ip_requests_per_minute": 100,
  "severity_map": {
    "sqli_attempts_per_ip": "CRITICAL",
    "failed_login_per_ip_per_minute": "HIGH",
    "rogue_device_count": "HIGH",
    "..."
  }
}
```

---

#### `PUT /thresholds`

Update threshold configuration. Changes take effect immediately (hot-reload).

```bash
curl -X PUT http://localhost:8000/thresholds \
  -H "Content-Type: application/json" \
  -d '{
    "failed_login_per_ip_per_minute": 3,
    "sqli_attempts_per_ip": 1,
    "http_5xx_per_minute": 5
  }'
```

**Response:**
```json
{
  "status": "updated",
  "thresholds": { "..." }
}
```

---

#### `GET /alerts?limit=500`

Returns the last N alert entries.

```bash
curl "http://localhost:8000/alerts?limit=100"
```

**Response:** Array of Alert objects:
```json
[
  {
    "id": "a1b2c3d4-...",
    "timestamp": "2026-03-14T09:26:15",
    "threshold_name": "failed_login_per_ip_per_minute",
    "current_value": 8.0,
    "threshold_value": 5.0,
    "severity": "HIGH",
    "ip_address": "192.168.1.55",
    "description": "8 failed logins from 192.168.1.55 in last minute",
    "auto_blocked": false
  }
]
```

---

### 7. SMTP Email Alerting

#### `GET /smtp-status`

Check if email alerting is configured and enabled.

```bash
curl http://localhost:8000/smtp-status
```

**Response:**
```json
{
  "enabled": false,
  "configured": false,
  "last_sent": null
}
```

---

#### `POST /test-email`

Send a test alert email to verify SMTP configuration.

```bash
curl -X POST http://localhost:8000/test-email
```

**Response:**
```json
{ "success": true, "error": "" }
```
or
```json
{ "success": false, "error": "SMTP not configured — set SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_TO" }
```

---

### 8. Port Scanner

#### `POST /scan-ports`

Trigger an immediate nmap port scan.

```bash
curl -X POST http://localhost:8000/scan-ports
```

Optional body:
```json
{
  "target": "localhost",
  "ports": "22,80,443,3306,5432,6379,8080,27017"
}
```

**Response:**
```json
{
  "target": "localhost",
  "timestamp": "2026-03-14T09:26:15",
  "scan_time": "3.2s",
  "open_ports": [
    { "port": 22, "protocol": "tcp", "state": "open", "service": "ssh", "version": "OpenSSH 8.9" },
    { "port": 8000, "protocol": "tcp", "state": "open", "service": "http-alt", "version": "uvicorn" }
  ],
  "unexpected_ports": [],
  "allowed_ports": [22, 80, 443, 8000, 5173],
  "mock_data": false
}
```

> If nmap is not installed, returns mock data with `"mock_data": true` and `"install": "sudo apt install nmap"`.

---

#### `GET /port-scan-history?limit=10`

Returns the last N scan results.

```bash
curl "http://localhost:8000/port-scan-history?limit=5"
```

---

#### `PUT /allowed-ports`

Update the allowlist of expected open ports.

```bash
curl -X PUT http://localhost:8000/allowed-ports \
  -H "Content-Type: application/json" \
  -d '{"ports": [22, 80, 443, 8000, 5173]}'
```

---

## Frontend Pages & Navigation

| Route | Page | Description |
|---|---|---|
| `/` | **Home** | Landing page |
| `/dashboard` | **Dashboard** | Main SOC command center — stat cards, agent feed, incident details |
| `/monitor` | **Live Monitor** | Real-time threat dashboard — live log feed, stats, thresholds, alerts, port scanner |
| `/investigation` | **Investigation** | Visual agent pipeline diagram |
| `/report` | **Report** | Full incident report viewer |
| `/about` | **Architecture** | Project info and tech stack |

### Key UI Features

- **SSE Live Feed** — Green pulsing dot = connected via SSE, Grey = polling fallback
- **LLM Badge** — Blue = Groq cloud, Green = Ollama local
- **Threat Monitor** — Dark SOC-aesthetic page with colour-coded log rows, stat cards, threshold editor, alert timeline, port scan panel

---

## How to Connect

### Frontend → Backend

The frontend connects to the backend at `http://localhost:8000` by default.

To change this, create `frontend/.env`:
```env
VITE_API_BASE_URL=http://localhost:8000
```

All API calls are defined in `frontend/src/lib/api.ts`. SSE connections are made via the browser's native `EventSource` API.

### CORS

The backend allows these origins:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000`
- `http://localhost:8080`
- All `127.0.0.1` equivalents

If your frontend runs on a different port, add it to the `origins` list in `backend/server.py`.

### SSE Connections

The frontend maintains two persistent SSE connections:

1. **`/stream`** — receives every log event in real time
2. **`/alerts/live`** — receives threshold breach alerts

Both auto-reconnect on failure with a 3-second retry.

---

## Step-by-Step Usage Guide

### Option A: Full AI Analysis (Backend Required)

1. Start the backend: `uv run uvicorn server:app --reload --host 0.0.0.0 --port 8000`
2. Start the frontend: `npm run dev`
3. Generate logs: `cd backend && uv run python generate_chaos_logs.py`
4. Open **http://localhost:5173/dashboard**
5. Click **"Start Investigation"**
6. Wait 3–10 minutes (LLM processing)
7. Check the **Report** page when status returns to idle

### Option B: Real-Time Monitoring (No AI Agents Needed)

1. Start the backend (the log watcher starts automatically)
2. Start the frontend
3. Navigate to **http://localhost:5173/monitor**
4. Watch live log events stream in
5. Configure thresholds in the collapsible panel
6. Alerts appear when thresholds are breached

### Option C: Frontend Demo (No Backend)

1. Open **http://localhost:5173/dashboard**
2. Select an attack type from the dropdown
3. Click **"Run Simulation"** — plays a scripted demo in the browser

---

## Real-Time Monitoring Setup

The log watcher (`backend/log_watcher.py`) starts automatically with the backend and attempts to watch these log sources (in order of priority):

| Source | Path | What it Detects |
|---|---|---|
| SSH Auth | `/var/log/auth.log` | Failed/successful logins, sudo usage |
| UFW Firewall | `/var/log/ufw.log` | Blocked connections, port scans |
| Nginx | `/var/log/nginx/access.log` | SQL injection, 4xx/5xx floods |
| Audit | `/var/log/audit/audit.log` | Sensitive file access |
| DHCP | `/var/log/dhcpd.log` | Rogue device detection |
| DNS | `/var/log/named/default` or `/var/log/pihole.log` | DNS anomalies |
| Syslog | `/var/log/syslog` | General anomalies |
| Custom | `WATCH_LOG_PATH` from `.env` | Whatever you specify |
| **Fallback** | *(synthetic generator)* | Simulated attack data every 2 seconds |

**If no log files are accessible** (e.g., running as non-root or on macOS/Windows), the watcher automatically falls back to generating synthetic log events for demonstration purposes.

### To Watch a Custom Log File

Set in `backend/.env`:
```env
WATCH_LOG_PATH=/path/to/your/logfile.log
```

---

## Gmail Email Alerts Setup

To receive email notifications when HIGH/CRITICAL alerts fire:

1. **Generate a Gmail App Password:**
   - Go to https://myaccount.google.com/apppasswords
   - Sign in and select "Mail" → "Other (Custom name)" → enter "Cyberguard"
   - Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

2. **Configure `.env`:**
   ```env
   SMTP_ENABLED=true
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your.email@gmail.com
   SMTP_PASSWORD=abcd efgh ijkl mnop
   ALERT_EMAIL_TO=soc-team@company.com
   ALERT_MIN_SEVERITY=HIGH
   ALERT_COOLDOWN_MINUTES=5
   ```

3. **Test it:**
   ```bash
   curl -X POST http://localhost:8000/test-email
   ```

4. **Check inbox** — you should receive a test alert email within 30 seconds.

> **Note:** Gmail requires 2-Step Verification to be enabled before you can create App Passwords. Regular passwords will NOT work.

---

## Ollama Local LLM Setup

To use a local LLM instead of Groq cloud:

1. **Install Ollama:** https://ollama.ai
2. **Pull the model:**
   ```bash
   ollama pull deepseek-r1:1.5b
   ```
3. **Configure `.env`:**
   ```env
   LLM_BACKEND=ollama
   OLLAMA_MODEL=deepseek-r1:1.5b
   ```
4. **Verify:**
   ```bash
   curl http://localhost:8000/llm-status
   # → {"backend": "ollama", "model": "ollama/deepseek-r1:1.5b", "ollama_available": true}
   ```

> Local inference is slower (~2–5 min per agent). Set `request_timeout=120` for patience. Groq is recommended for speed.

---

## Background Services

These run automatically when the backend starts:

| Service | Description | Interval |
|---|---|---|
| **Log Watcher** | Monitors system logs, parses events, streams via SSE | Continuous |
| **Threshold Engine** | Evaluates every log event against configurable rules | Per-event |
| **Alert Mailer** | Sends email for HIGH/CRITICAL alerts | Per-alert (with cooldown) |
| **Port Scanner** | Scans localhost for open ports | Every 30 minutes |
| **Redis Publisher** | Publishes events to Redis for cross-process distribution | Per-event *(optional)* |

### Redis (via docker-compose)

Redis is managed via `docker-compose.yml` at the project root. It provides persistent event storage and faster retrievals.

```bash
# Start Redis
docker compose up -d

# Verify
docker exec cyberguard-redis redis-cli ping   # → PONG

# Subscribe to live events
docker exec cyberguard-redis redis-cli subscribe cyberguard:logs

# Stop Redis
docker compose down
```

The `docker-compose.yml` configures:
- **Persistent volume** (`redis-data`) — data survives container restarts
- **Append-only file** (AOF) — durable writes
- **256MB memory limit** with LRU eviction
- **Health check** every 10 seconds
- **Auto-restart** unless manually stopped

If Redis is NOT running, the system works fine with in-memory queues — no data loss, just no cross-restart persistence.

---

## Troubleshooting

### Backend won't start

```bash
# Check if port 8000 is in use
lsof -i :8000
# Kill the process
kill <PID>
```

### "Groq rate limit" errors

Normal — the crew runs at 3 req/min for the free tier. Wait for it to complete (3–10 min).

### No log events streaming

- The system falls back to synthetic logs if no system logs are accessible
- Check `curl -N http://localhost:8000/stream` — you should see events
- If nothing, check backend console for errors

### CORS errors in browser

Add your frontend's origin to the `origins` list in `backend/server.py`.

### Email not sending

1. Check `curl http://localhost:8000/smtp-status` — ensure `configured: true`
2. Ensure you're using a **Gmail App Password**, NOT your account password
3. Ensure 2-Step Verification is enabled on your Google account
4. Check `backend/data/email_audit.json` for error details

### nmap scan returns mock data

Install nmap: `sudo apt install nmap`

### Frontend can't connect

- Ensure backend is running on port 8000
- Check `frontend/.env` or `frontend/src/lib/api.ts` for `BASE_URL`
- Check browser DevTools Network tab for failed requests

---

## Complete Endpoint Summary Table

| # | Method | Endpoint | Category | Description |
|---|--------|----------|----------|-------------|
| 1 | POST | `/run-simulation` | Core | Start 6-agent AI analysis |
| 2 | GET | `/status` | Core | Check pipeline status (running/idle) |
| 3 | GET | `/logs` | Core | Get raw CSV logs |
| 4 | POST | `/upload-logs` | Core | Upload custom CSV for analysis |
| 5 | GET | `/report` | Report | Raw Markdown incident report |
| 6 | GET | `/report/raw` | Report | Alias for /report |
| 7 | GET | `/report/structured` | Report | Parsed JSON report |
| 8 | GET | `/llm-status` | LLM | Active LLM backend info |
| 9 | GET | `/anomaly-report` | ML | IsolationForest anomaly summary |
| 10 | GET | `/stream` | SSE | Live log event stream |
| 11 | GET | `/stream/replay` | SSE | Replay last N events |
| 12 | GET | `/alerts/live` | SSE | Live alert stream |
| 13 | POST | `/auto-respond` | Response | Trigger iptables auto-response |
| 14 | GET | `/response-audit` | Response | Auto-response action log |
| 15 | GET | `/thresholds` | Alerts | Get threshold config |
| 16 | PUT | `/thresholds` | Alerts | Update threshold config |
| 17 | GET | `/alerts` | Alerts | Get alert history |
| 18 | GET | `/smtp-status` | Email | SMTP configuration status |
| 19 | POST | `/test-email` | Email | Send test alert email |
| 20 | POST | `/scan-ports` | Scanner | Trigger nmap scan |
| 21 | GET | `/port-scan-history` | Scanner | Get scan history |
| 22 | PUT | `/allowed-ports` | Scanner | Update port allowlist |

---

*Built with ❤️ using CrewAI, FastAPI, React, and Groq LLaMA 3.3 — Cyberguard v2.0*
