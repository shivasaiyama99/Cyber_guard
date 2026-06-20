# 🛡️ VulnLab — Working Description & File Contents

> ⚠️ **THIS APPLICATION IS INTENTIONALLY INSECURE.** It is designed for local security testing only — **never deploy to a public network.**

## What Is VulnLab?

**VulnLab** is a deliberately vulnerable Flask web application built as a **security testing target** for the **Cyberguard** monitoring system. It exposes a wide range of common web vulnerabilities (SQL injection, XSS, command injection, IDOR, etc.) so that Cyberguard's detection, alerting, and fail2ban integration can be tested against realistic attack scenarios.

---

## 📁 Directory Structure

```
test_app/
├── app.py                 # Main Flask application (599 lines)
├── init_db.py             # Database initialization script
├── ddos_simulate.py       # DDoS attack simulator script
├── database.db            # SQLite database (auto-created)
├── pyproject.toml         # Project metadata & dependencies
├── run.md                 # How-to-run instructions
├── static/
│   └── style.css          # Application CSS styles
├── templates/             # Jinja2 HTML templates
│   ├── base.html          #   → Shared layout
│   ├── index.html         #   → Home page
│   ├── login.html         #   → Login form
│   ├── products.html      #   → Product listing
│   ├── profile.html       #   → User profile
│   ├── ping.html          #   → Network ping tool
│   ├── upload.html        #   → File upload page
│   ├── comments.html      #   → Comment board
│   ├── admin.html         #   → Admin panel
│   ├── logs.html          #   → System log viewer
│   └── ddos.html          #   → DDoS simulator UI
├── uploads/               # Uploaded files (unrestricted)
├── backup/
│   └── db_dump.sql        # Exposed database backup (recon target)
├── secret/
│   └── credentials.txt    # Exposed credentials file (recon target)
└── .venv/                 # Python virtual environment
```

---

## 📄 File-by-File Description

### 1. `app.py` — Main Application

The core Flask server (**599 lines**) that runs on **port 9090**. It contains:

#### Access Log Middleware
Every request is logged in **nginx combined format** to `backend/data/vulnlab_access.log`, enabling Cyberguard's `log_watcher.py` to parse and analyze traffic in real time.

#### Web Pages (Vulnerable Endpoints)

| Route | Vulnerability | Description |
|---|---|---|
| `/login` | **SQL Injection + Brute Force** | Login form using raw f-string SQL queries. No rate limiting or account lockout. |
| `/products` | **SQL Injection** | Product search/filter with direct string interpolation in SQL (`search`, `id`, `category` params). |
| `/profile/<user_id>` | **IDOR** | View any user's profile — no authorization check on who is requesting. |
| `/ping` | **Command Injection** | Runs user input directly in a shell via `subprocess.run(shell=True)`. |
| `/upload` | **Unrestricted File Upload** | No file-type validation, no size limit, original filename preserved. |
| `/comments` | **Stored XSS** | Comments stored as raw HTML/JS and rendered unescaped in the template. |
| `/admin` | **Broken Access Control** | Admin panel accessible without any authentication. |
| `/logs` | **Info Disclosure + Command Injection** | Reads system log files via `tail`; the `file` parameter is injectable. |

#### API Endpoints

| Route | Method | Vulnerability |
|---|---|---|
| `/api/users` | GET | SQL Injection via `search` param |
| `/api/products` | GET | SQL Injection via `id` or `search` param |
| `/api/login` | POST | SQL Injection + no rate limiting |
| `/api/logs` | GET | System log exposure via API |
| `/api/system-info` | GET | Exposes hostname, OS, kernel, processes, network info |
| `/api/active-connections` | GET | Exposes active network connections |
| `/config` | GET | Leaks DB path, secret key, upload dir, debug flag |
| `/status` | GET | Health check (returns app name/version) |

#### DDoS Simulator Endpoints

| Route | Method | Description |
|---|---|---|
| `/ddos` | GET/POST | Web UI to start/stop DDoS attacks against a target |
| `/api/ddos` | POST | API to trigger DDoS simulation remotely |
| `/api/ddos/stop` | POST | API to stop a running attack |
| `/api/ddos/status` | GET | Check if an attack is currently running |

#### Hidden / Recon Targets

| Route | Description |
|---|---|
| `/robots.txt` | Leaks paths: `/admin`, `/backup`, `/secret`, `/config` |
| `/.env` | Serves the environment file directly |
| `/backup/<file>` | Serves files from the `backup/` directory |
| `/secret/<file>` | Serves files from the `secret/` directory |

---

### 2. `init_db.py` — Database Initialization

Creates and seeds the SQLite database (`database.db`) with three tables:

| Table | Records | Purpose |
|---|---|---|
| **users** | 10 | Brute-force & SQLi targets. Stores username, plaintext password, email, role, credit card, and SSN. |
| **products** | 12 | SQLi targets. Cybersecurity-themed products with name, description, price, category, stock. |
| **comments** | 5 | Stored XSS target. Pre-seeded sample comments. |

**Sample Credentials:**

| Username | Password | Role |
|---|---|---|
| admin | admin123 | admin |
| john | password | user |
| jane | letmein | user |
| alice | trustno1 | editor |

---

### 3. `ddos_simulate.py` — DDoS Attack Simulator

A standalone CLI tool (**371 lines**) that simulates various DDoS attacks for testing Cyberguard's detection capabilities.

**Attack Types:**

| Type | Description |
|---|---|
| `http` | HTTP flood — rapid GET/POST requests with SQLi payloads, brute-force attempts, and path scanning |
| `syn` | TCP SYN flood — rapid connect/close cycles at maximum rate |
| `slowloris` | Holds connections open with partial HTTP headers to exhaust server resources |
| `mixed` | Rotates through all three attack types across threads |

**Usage:**
```bash
python ddos_simulate.py --target 192.168.1.100 --port 9090 --attack http --duration 30 --threads 20
```

Features a thread-safe `AttackStats` class that tracks requests sent, connections made, errors, and requests-per-second in real time.

---

### 4. `pyproject.toml` — Project Config

```toml
[project]
name = "vulnlab"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = ["flask>=3.0"]
```

---

### 5. Supporting Files

| File | Description |
|---|---|
| `static/style.css` | Full application CSS (17 KB) — dark hacker-themed styling |
| `backup/db_dump.sql` | Exposed SQL dump — directory brute-force discovery target |
| `secret/credentials.txt` | Exposed credentials — directory brute-force discovery target |
| `templates/*.html` | 11 Jinja2 templates rendered by Flask routes |

---

## 🚀 How to Run

```bash
cd test_app

# Initialize the database (first run or to reset)
uv run python init_db.py

# Start the server
uv run python app.py
```

App runs at **http://localhost:9090**.

---

## 🧩 How It Fits Into Cyberguard

VulnLab acts as the **attack surface** that Cyberguard monitors:

1. **`app.py`** logs every request in nginx format → `backend/data/vulnlab_access.log`
2. **`log_watcher.py`** (in the Cyberguard backend) parses these logs in real time
3. Cyberguard's AI agent detects attacks (SQLi, brute-force, DDoS, etc.) and triggers alerts
4. **`ddos_simulate.py`** can generate realistic attack traffic to stress-test detection
