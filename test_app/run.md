# VulnLab — How to Run

> ⚠️ **This is an intentionally vulnerable application. DO NOT deploy to any public network.**

## Prerequisites

- **Python** ≥ 3.10
- **uv** (Python package manager) — [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

## Quick Start

```bash
# 1. Navigate to the test_app directory
cd test_app

# 2. Initialize the database (only needed on first run, or to reset data)
uv run python init_db.py

# 3. Start the server
uv run python app.py
```

The app will be available at **http://localhost:9090**.

## If Port 9090 Is Already In Use

Kill the existing process first, then restart:

```bash
lsof -ti:9090 | xargs kill -9
uv run python app.py
```

## Available Routes

| Route | Description |
| --- | --- |
| `/` | Home page |
| `/login` | Login page (brute-force & SQLi target) |
| `/products` | Product listing (SQLi target) |
| `/profile/<user_id>` | User profile (IDOR target) |
| `/ping` | Network ping tool (command injection target) |
| `/upload` | File upload (unrestricted upload target) |
| `/comments` | Comment board (stored XSS target) |
| `/admin` | Admin panel (hidden directory target) |
| `/api/users` | Users API (SQLi target) |
| `/api/products` | Products API (SQLi target) |
| `/api/login` | Login API (no rate limit, SQLi target) |
| `/config` | App configuration (info disclosure) |
| `/robots.txt` | Robots file (recon target) |
| `/.env` | Exposed environment file |
| `/status` | Health check endpoint |

## Test Credentials

| Username | Password | Role |
| --- | --- | --- |
| admin | admin123 | admin |
| john | password | user |
| jane | letmein | user |
| bob | qwerty | user |
| alice | trustno1 | editor |

## Tech Stack

- **Framework**: Flask 3.x
- **Database**: SQLite (`database.db`)
- **Package Manager**: uv
- **Port**: 9090
