# External Integrations

**Analysis Date:** 2025-02-05

## APIs & External Services

**LLM Models:**
- Groq - Primary LLM provider for `llama-3.3-70b-versatile`.
  - SDK/Client: `langchain-groq`, `litellm`.
  - Auth: `GROQ_API_KEY` (inferred from `backend/src/cyberguard/crew.py`).

**Threat Intelligence:**
- AbuseIPDB - IP reputation and confidence scoring.
  - SDK/Client: `requests` (direct REST calls).
  - Auth: `ABUSEIPDB_API_KEY` (`backend/src/cyberguard/tools/custom_tools.py`).
- VirusTotal - Malware and security vendor detection for IPs.
  - SDK/Client: `requests` (direct REST calls).
  - Auth: `VIRUSTOTAL_API_KEY` (`backend/src/cyberguard/tools/custom_tools.py`).
- Shodan / InternetDB - Open ports and vulnerability indexing (Free tier).
  - SDK/Client: `requests` (direct REST calls).
  - Auth: None required (Free tier).

## Data Storage

**Databases:**
- None (Local JSON and CSV used).
  - Threat Database: `backend/data/threat_db.json`.
  - Simulation Logs: `backend/data/simulation_logs.csv`.

**File Storage:**
- Local Filesystem only.
  - Incident Reports: `backend/incident_report.md`.
  - Generated reports are saved in `backend/reports/` and `backend/incident_report.md`.

**Caching:**
- CrewAI Cache (disabled in `backend/src/cyberguard/crew.py`).
- LiteLLM Cache (not explicitly configured).

## Authentication & Identity

**Auth Provider:**
- Custom / None (Local development focus).
  - `fastapi-sso` 0.20 - Dependency exists in `backend/pyproject.toml`, but not explicitly implemented in `backend/server.py`.

## Monitoring & Observability

**Error Tracking:**
- None.

**Logs:**
- Python `logging` module in backend (`backend/src/cyberguard/main.py`).
- Frontend console logs and `use-toast.ts` for UI notifications.

## CI/CD & Deployment

**Hosting:**
- Not specified (Local/Docker expected).

**CI Pipeline:**
- None.

## Environment Configuration

**Required env vars:**
- `GROQ_API_KEY`: Required for LLM execution.
- `ABUSEIPDB_API_KEY`: Required for threat intel enrichment.
- `VIRUSTOTAL_API_KEY`: Optional but recommended for malware analysis.
- `VITE_API_BASE_URL`: Frontend configuration to locate backend API (defaults to `http://localhost:8000`).

**Secrets location:**
- `backend/.env` file (local development only).

## Webhooks & Callbacks

**Incoming:**
- `/run-simulation` (POST) - Triggers the CrewAI agent execution from the frontend.
- `/upload-logs` (POST) - Accepts CSV log file uploads for processing.

**Outgoing:**
- External calls to Groq, AbuseIPDB, VirusTotal, and Shodan APIs via `requests`.

---

*Integration audit: 2025-02-05*
