import asyncio
import csv
import io
import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sse_starlette.sse import EventSourceResponse
import re
from typing import Dict, Any, List
from pydantic import BaseModel

from database import connect_to_mongodb, close_mongodb_connection, get_db
import database as db_module
from auth import (
    get_current_user, create_user_in_db, authenticate_user_in_db,
    create_access_token, save_session, delete_session,
    oauth2_scheme, verify_google_token, google_login_or_create,
    register_session, unregister_session, get_active_emails,
    _active_sessions,
)

# Ensure the backend and src directories are on the path to import files correctly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
SRC_DIR = os.path.join(CURRENT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

def get_data_file_path(filename: str) -> str:
    if os.environ.get("IS_VERCEL") == "true":
        base = os.path.basename(filename)
        if "simulation_logs.csv" in filename:
            tmp_data_dir = "/tmp/data"
            os.makedirs(tmp_data_dir, exist_ok=True)
            return os.path.join(tmp_data_dir, "simulation_logs.csv")
        return os.path.join("/tmp", base)
    else:
        return os.path.join(CURRENT_DIR, filename)

from cyberguard.main import run as run_crew  # noqa: E402
from cyberguard.crew import ACTIVE_LLM_BACKEND, ACTIVE_LLM_MODEL  # noqa: E402
from log_watcher import (  # noqa: E402
    start_watcher, subscribe, unsubscribe,
    subscribe_alerts, unsubscribe_alerts,
    subscribe_agent, unsubscribe_agent,
    broadcast_agent_message, get_agent_messages_history,
    replay_buffer, set_on_new_row, broadcast_alert, set_session_active as set_log_session_active,
    lock_csv, unlock_csv, set_live_monitor
)

from tail_watcher import start_watcher as _legacy_start_watcher  # noqa: E402  # keep import for compat
from anomaly_detector import AnomalyDetector  # noqa: E402
from auto_responder import execute_response, get_audit_log  # noqa: E402
from redis_pipeline import publisher as redis_publisher  # noqa: E402
from threshold_engine import ThresholdEngine, ThresholdConfig, Alert  # noqa: E402
from alert_mailer import alert_mailer  # noqa: E402
from port_scanner import port_scanner  # noqa: E402

# Shared anomaly detector instance
anomaly_detector = AnomalyDetector()

# Threshold engine instance
threshold_engine = ThresholdEngine()

# Anomaly summary string injected into SENTRY agent context
anomaly_context: Optional[str] = None

# Default dry-run mode from env
AUTO_RESPOND_DRY_RUN = os.environ.get("AUTO_RESPOND_DRY_RUN", "true").strip().lower() != "false"

# Incident counter (loaded from DB on startup)
_incident_counter: int = 0

# Session state tracking
_session_active: bool = False
_current_incident_md: Optional[str] = None
_current_structured_report: Optional[Dict[str, Any]] = None
_current_logs_content: Optional[str] = None


def _threshold_callback(row: dict):
    """Called by log_watcher for every new row — evaluate thresholds."""
    alert = threshold_engine.evaluate(row, replay_buffer)
    if alert is not None:
        alert_dict = alert.model_dump()
        broadcast_alert(alert_dict)
        # Email is sent by threshold_engine.make_alert() via send_alert_threaded


async def _periodic_port_scan():
    """Run port scan every 30 minutes."""
    while True:
        await asyncio.sleep(1800)  # 30 min
        try:
            await port_scanner.scan()
        except Exception:
            pass


async def _init_incident_counter():
    """Set incident counter from last incident in DB."""
    global _incident_counter
    if db_module.incidents_collection is not None:
        try:
            last = await db_module.incidents_collection.find_one(
                sort=[("_id", -1)]
            )
            if last and last.get("incident_id"):
                parts = last["incident_id"].split("-")
                if len(parts) >= 3:
                    _incident_counter = int(parts[-1])
        except Exception:
            pass


def _next_incident_id() -> str:
    global _incident_counter
    _incident_counter += 1
    year = datetime.utcnow().year
    return f"INC-{year}-{_incident_counter:03d}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to MongoDB (graceful — works without it)
    await connect_to_mongodb()
    await _init_incident_counter()

    # Cleanup only the incident report on startup (preserve CSV for investigation resume)
    report_path = get_data_file_path("incident_report.md")
    if os.path.exists(report_path):
        try:
            os.remove(report_path)
            print(f"Cleaned up legacy file: incident_report.md")
        except Exception as e:
            print(f"Failed to cleanup incident_report.md: {e}")

    # Initialize log_watcher session state
    set_log_session_active(False)
    # Enable live monitor mode so SSE feed works immediately on startup
    set_live_monitor(True)
    print(f"Server started — _session_active = {_session_active}, live_monitor = True")
    csv_check_path = get_data_file_path("data/simulation_logs.csv")
    csv_exists = os.path.exists(csv_check_path)
    print(f"simulation_logs.csv exists: {csv_exists}")
    if csv_exists:
        print("[OK] Previous CSV found - investigation can resume")
    # Connect to Redis (graceful — works without it)
    await redis_publisher.connect()
    # Wire threshold engine into log watcher pipeline
    set_on_new_row(_threshold_callback)
    
    watcher_task = None
    scan_task = None
    if os.environ.get("IS_VERCEL") != "true":
        # Start the live log ingestor as a background task
        watcher_task = asyncio.create_task(start_watcher())
        scan_task = asyncio.create_task(_periodic_port_scan())
        
    yield
    
    if scan_task:
        scan_task.cancel()
    if watcher_task:
        watcher_task.cancel()
    for t in (watcher_task, scan_task):
        if t:
            try:
                await t
            except asyncio.CancelledError:
                pass
    await redis_publisher.close()
    await close_mongodb_connection()


app = FastAPI(title="Cyberguard API", version="1.0.0", lifespan=lifespan)

# CORS for local frontend (include 8080 for alternate dev server port)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory status flag
_status: str = "idle"


@app.get("/test-verify-123")
def test_verify():
    return {"message": "ALIVE"}


# ──────────────────────────────────────────────────────────────────────────────
# Helper: serialize ObjectId
# ──────────────────────────────────────────────────────────────────────────────

def _serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-safe dict (ObjectId → str)."""
    if doc is None:
        return {}
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Recursively convert datetime fields
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


@app.get("/session-status")
def get_session_status():
    global _session_active
    return {"session_active": _session_active}


# ──────────────────────────────────────────────────────────────────────────────
# Simulation & Report Logic
# ──────────────────────────────────────────────────────────────────────────────

async def _run_simulation_task():
    print("\n=== _run_simulation_task() STARTED ===")
    global _status, anomaly_context, _session_active, _current_incident_md, _current_structured_report
    success = False
    crew_failed = False
    try:
        _status = "running"
        print(f"=== BEFORE: _session_active = {_session_active} ===")
        _session_active = True
        set_log_session_active(True)
        print(f"=== AFTER: _session_active = {_session_active} ===")
        _current_incident_md = None
        _current_structured_report = None
        print("=== Starting CrewAI pipeline ===")

        # Run anomaly detection on current logs before passing to crew
        csv_path = get_data_file_path("data/simulation_logs.csv")
        print(f"=== Checking for CSV at: {csv_path} ===")
        if os.path.exists(csv_path):
            print(f"=== CSV found! Running anomaly detection ===")
            try:
                import anyio
                summary = await anyio.to_thread.run_sync(anomaly_detector.score_file, csv_path)
                if summary["anomalous_ips"]:
                    anomaly_context = (
                        "Pre-analysis anomaly detection flagged the following IPs as anomalous: "
                        + ", ".join(summary["anomalous_ips"])
                    )
                    os.environ["ANOMALY_CONTEXT"] = anomaly_context
                else:
                    anomaly_context = None
                    os.environ.pop("ANOMALY_CONTEXT", None)
            except Exception as e:
                print(f"=== Anomaly detection error (non-fatal): {e} ===")
        else:
            print(f"=== WARNING: CSV NOT FOUND at {csv_path} ===")
            print(f"=== CrewAI will run but may fail without data ===")

        # Call existing business logic (do not modify)
        import anyio
        print("=== Calling run_crew() now... ===")

        # Broadcast pre-analysis agent messages
        broadcast_agent_message("SYSTEM", "Initializing CrewAI investigation pipeline...", "info")
        broadcast_agent_message("SENTRY", "Scanning log entries for suspicious patterns...", "info")
        broadcast_agent_message("HUNTER", "Preparing threat intelligence lookups...", "info")
        broadcast_agent_message("DETECTIVE", "Reconstructing attack timeline...", "info")
        broadcast_agent_message("JUDGE", "Preparing risk assessment framework...", "info")
        broadcast_agent_message("MEDIC", "Loading containment playbooks...", "info")
        broadcast_agent_message("SCRIBE", "Ready to compile incident report...", "info")

        try:
            await anyio.to_thread.run_sync(run_crew)
            print("=== CrewAI pipeline completed ===")
        except Exception as crew_error:
            crew_failed = True
            import traceback
            print(f"=== CrewAI ERROR: {crew_error} ===")
            traceback.print_exc()
            broadcast_agent_message("SYSTEM", f"Investigation failed: {str(crew_error)}", type="error")

        # After crew completes, run auto-response engine
        report_path = get_data_file_path("incident_report.md")
        print(f"=== Checking for report at: {report_path} ===")
        print(f"=== Report file exists: {os.path.exists(report_path)} ===")

        if os.path.exists(report_path):
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    md = f.read()
                print(f"=== Report file size: {len(md)} chars ===")
                if len(md) > 0:
                    print(f"=== Report first 300 chars: {md[:300]} ===")
                structured = _parse_report_md(md)
                print(f"=== Parsed structured report: risk_score={structured.get('risk_score')}, severity={structured.get('severity')} ===")
                await anyio.to_thread.run_sync(execute_response, structured, AUTO_RESPOND_DRY_RUN)

                # --- Save to MongoDB ---
                print("=== Attempting MongoDB save ===")
                await _save_incident_and_report(md, structured)

                # Update current session data
                _current_incident_md = md
                _current_structured_report = structured
                print(f"=== Successfully cached structured report in memory ===")

                # Broadcast post-analysis agent messages with actual results
                broadcast_agent_message("SYSTEM", "CrewAI analysis complete", "success")
                attack_type = structured.get("attack_type", "Unknown")
                source_ip = structured.get("source_ip", "Unknown")
                risk_score = structured.get("risk_score", "0")
                severity = structured.get("severity", "UNKNOWN")
                broadcast_agent_message("SENTRY", f"Detected attack type: {attack_type}", "success")
                broadcast_agent_message("HUNTER", f"Malicious IP identified: {source_ip}", "success")
                broadcast_agent_message("JUDGE", f"Risk assessment complete — Score: {risk_score}/100 ({severity})", "success")
                broadcast_agent_message("MEDIC", "Generating containment recommendations...", "info")
                actions = structured.get("recommended_actions", [])
                if actions:
                    broadcast_agent_message("MEDIC", f"Containment actions: {', '.join(actions[:3])}", "success")
                broadcast_agent_message("SCRIBE", "Incident report complete — ready for review", "success")

                success = True
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"=== ERROR in simulation: {str(e)} ===")
                broadcast_agent_message("SYSTEM", f"Report processing failed: {str(e)}", type="error")
        else:
            print("=== WARNING: CrewAI completed but incident_report.md was NOT created ===")
            if not crew_failed:
                broadcast_agent_message("SYSTEM", "Investigation finished but no report was generated", type="warning")
    finally:
        _status = "complete" if success else "idle"
        print(f"=== Simulation task finished, status={_status} ===")


async def _save_incident_and_report(md_content: str, structured: dict):
    """Persist incident and report to MongoDB after simulation."""
    if db_module.incidents_collection is None:
        print("Error saving to MongoDB: Database connection is None")
        return
    try:
        inc_id = _next_incident_id()
        risk_raw = structured.get("risk_score")
        risk_score = int(risk_raw) if risk_raw and str(risk_raw).isdigit() else 0

        agent_notes_list = []
        for note in structured.get("agent_notes", []):
            if isinstance(note, dict):
                agent_notes_list.append(f"[{note.get('agent', '')}] {note.get('note', '')}")
            else:
                agent_notes_list.append(str(note))
                
        severity_val = structured.get("severity", "")
        if severity_val:
            severity_val = str(severity_val).upper()

        incident_doc = {
            "incident_id": inc_id,
            "attack_type": structured.get("attack_type", ""),
            "risk_score": risk_score,
            "severity": severity_val,
            "source_ip": structured.get("source_ip", ""),
            "timestamp": datetime.utcnow(),
            "status": "open",
            "agent_notes": agent_notes_list,
        }
        result = await db_module.incidents_collection.insert_one(incident_doc)
        print(f"=== Incident saved: {result.inserted_id} ===")

        report_doc = {
            "incident_id": inc_id,
            "markdown_content": md_content,
            "structured_json": structured,
            "created_at": datetime.utcnow(),
            "created_by": "system",
        }
        await db_module.reports_collection.insert_one(report_doc)
    except Exception as e:
        print("Error saving to MongoDB:", str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Existing Endpoints (Protected / Public as specified)
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/run-simulation")
async def run_simulation(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    global _status, _session_active
    print("\n=== /run-simulation called ===")
    print(f"=== BEFORE: _session_active = {_session_active} ===")
    if _status == "running":
        raise HTTPException(status_code=409, detail="Simulation already running")
    _session_active = True
    set_log_session_active(True)
    print(f"=== AFTER: _session_active = {_session_active} ===")
    unlock_csv()
    if os.environ.get("IS_VERCEL") == "true":
        await _run_simulation_task()
    else:
        background_tasks.add_task(_run_simulation_task)
    return {"accepted": True}


@app.get("/logs", response_class=PlainTextResponse)
def get_logs(path: Optional[str] = None):
    global _session_active
    print(f"GET /logs called — _session_active = {_session_active}")
    if not _session_active:
        return PlainTextResponse("timestamp,ip_address,user,status,endpoint\n", media_type="text/csv")

    # Return ONLY the uploaded CSV content — not synthetic additions
    logs_path = path or get_data_file_path("data/simulation_logs.csv")
    if not os.path.isabs(logs_path):
        logs_path = os.path.abspath(logs_path)
    if not os.path.exists(logs_path):
        return PlainTextResponse("timestamp,ip_address,user,status,endpoint\n", media_type="text/csv")
    try:
        with open(logs_path, "r", encoding="utf-8") as f:
            content = f.read()
        lines = [l for l in content.strip().split("\n") if l]
        count = len(lines) - 1  # subtract header
        print(f"Returning {count} log entries (stable CSV)")
        return PlainTextResponse(content, media_type="text/csv; charset=utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/count")
def get_logs_count():
    """Return the number of log entries in simulation_logs.csv."""
    logs_path = get_data_file_path("data/simulation_logs.csv")
    if not os.path.exists(logs_path):
        return {"count": 0}
    try:
        with open(logs_path, "r", encoding="utf-8") as f:
            # Count non-empty lines and subtract header
            lines = [l for l in f if l.strip()]
            count = max(0, len(lines) - 1)
        return {"count": count}
    except Exception:
        return {"count": 0}


@app.get("/report", response_class=PlainTextResponse)
def get_report(path: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    global _session_active, _current_incident_md
    if not _session_active or not _current_incident_md:
        return PlainTextResponse("", media_type="text/markdown")
        
    report_path = path or get_data_file_path("incident_report.md")
    if not os.path.isabs(report_path):
        report_path = os.path.abspath(report_path)
    if not os.path.exists(report_path):
        return PlainTextResponse(_current_incident_md, media_type="text/markdown")
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        return PlainTextResponse(content, media_type="text/markdown; charset=utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
def get_status():
    global _status, _session_active
    return {"status": _status, "session_active": _session_active}


@app.get("/test-db")
async def test_db():
    if db_module.incidents_collection is None:
        return {"status": "error", "message": "MongoDB is not connected"}
    try:
        test_doc = {
            "incident_id": "INC-TEST-001",
            "attack_type": "Test Attack",
            "risk_score": 50,
            "severity": "MEDIUM",
            "source_ip": "127.0.0.1",
            "timestamp": datetime.utcnow(),
            "status": "open",
            "agent_notes": ["This is a test note"]
        }
        result = await db_module.incidents_collection.insert_one(test_doc)
        return {
            "status": "success",
            "message": "Test document inserted successfully",
            "inserted_id": str(result.inserted_id),
            "collection": "incidents",
            "database": "cyberguard_db"
        }
    except Exception as e:
        return {"status": "error", "message": f"Insert failed: {str(e)}"}

@app.get("/db-status")
async def db_status():
    if db_module.db is None:
        return {
            "mongodb_connected": False,
            "database": None,
            "collections": [],
            "incidents_count": 0
        }
    try:
        collections = await db_module.db.list_collection_names()
        count = await db_module.incidents_collection.count_documents({})
        return {
            "mongodb_connected": True,
            "database": "cyberguard_db",
            "collections": collections,
            "incidents_count": count
        }
    except Exception as e:
        return {
            "mongodb_connected": False,
            "error": str(e)
        }


@app.get("/llm-status")
async def get_llm_status():
    """Return current LLM backend info and Ollama availability."""
    import httpx
    ollama_available = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            ollama_available = resp.status_code == 200
    except Exception:
        pass
    return {
        "backend": ACTIVE_LLM_BACKEND,
        "model": ACTIVE_LLM_MODEL,
        "ollama_available": ollama_available,
    }


@app.get("/anomaly-report")
def get_anomaly_report():
    """Return the anomaly detection summary from the last scoring run in current session."""
    global _session_active
    if not _session_active:
        return {"anomalous_count": 0, "anomalous_ips": [], "total_logs": 0}
    return anomaly_detector.get_summary()


@app.post("/upload-logs")
async def upload_logs(background_tasks: BackgroundTasks, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Accept a CSV upload, persist rows to MongoDB logs collection, then trigger the pipeline."""
    global _session_active
    print(f"\n=== /upload-logs called by user: {current_user.get('email', 'unknown')} ===")
    print(f"=== BEFORE: _session_active = {_session_active} ===")
    _session_active = True
    set_log_session_active(True)
    print(f"=== AFTER: _session_active = {_session_active} ===")
    try:
        dest_path = get_data_file_path("data/simulation_logs.csv")
        raw = file.file.read()
        print(f"=== File received: {len(raw)} bytes ===")
        with open(dest_path, "wb") as out:
            out.write(raw)
        print(f"=== File saved to: {dest_path} ===")

        # Parse CSV and save each row to MongoDB logs collection
        if db_module.logs_collection is not None:
            try:
                text = raw.decode("utf-8", errors="replace")
                reader = csv.DictReader(io.StringIO(text))
                docs = []
                for row in reader:
                    doc = {
                        "timestamp": row.get("timestamp") or row.get("Timestamp"),
                        "ip_address": row.get("ip_address") or row.get("source_ip") or row.get("IP"),
                        "user": row.get("user") or row.get("username") or row.get("User"),
                        "status": row.get("status") or row.get("Status") or row.get("action"),
                        "endpoint": row.get("endpoint") or row.get("url") or row.get("path"),
                        "uploaded_at": datetime.utcnow(),
                        "session_id": str(current_user.get("id", "")),
                    }
                    docs.append(doc)
                if docs:
                    await db_module.logs_collection.insert_many(docs)
            except Exception as e:
                print(f"[WARNING] Failed to parse CSV rows into MongoDB: {e}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    # Set csv locked flag to prevent log_watcher from overwriting simulation_logs.csv
    lock_csv()

    # Trigger the pipeline
    if os.environ.get("IS_VERCEL") == "true":
        print("=== Awaiting _run_simulation_task synchronously on Vercel ===")
        await _run_simulation_task()
    else:
        print("=== Adding _run_simulation_task to background tasks ===")
        background_tasks.add_task(_run_simulation_task)
    print("=== Returning response ===")
    return {"accepted": True}


@app.get("/report/raw", response_class=PlainTextResponse)
def get_report_raw(path: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    print("=== /report/raw called ===")
    print(f"=== _session_active = {_session_active} ===")
    report_path = path or get_data_file_path("incident_report.md")
    if not os.path.isabs(report_path):
        report_path = os.path.abspath(report_path)
    print(f"=== incident_report.md exists: {os.path.exists(report_path)} ===")
    if os.path.exists(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"=== returning {len(content)} chars ===")
            return PlainTextResponse(content, media_type="text/markdown; charset=utf-8")
        except Exception as e:
            print(f"=== error reading report: {e} ===")
            raise HTTPException(status_code=500, detail=str(e))
    # Fallback to in-memory content if file doesn't exist
    if _current_incident_md:
        print(f"=== returning in-memory report ({len(_current_incident_md)} chars) ===")
        return PlainTextResponse(_current_incident_md, media_type="text/markdown; charset=utf-8")
    print("=== no report available ===")
    return PlainTextResponse("", media_type="text/markdown")


def _parse_report_md(content: str) -> dict:
    import re
    from datetime import datetime
    
    structured: Dict[str, Any] = {
        "incident_id": None,
        "attack_type": None,
        "risk_score": "0",
        "severity": "MEDIUM",
        "source_ip": None,
        "targeted_service": None,
        "evidence": None,
        "recommended_actions": [],
        "agent_notes": [],
        "timeline": [],
        "timestamps": {}
    }

    # Problem 1: risk_score
    # Look for "Risk Score: <number>" pattern first (most reliable)
    risk_match = re.search(r'Risk\s+Score[:\s]+(\d+)', content, re.IGNORECASE)
    if not risk_match:
        # Try Total Risk Score
        risk_match = re.search(r'total.?risk.?score[^\d]*(\d+)', content, re.IGNORECASE)
    if not risk_match:
        # Last resort — find any score number
        risk_match = re.search(r'score[^\d]*(\d+)', content, re.IGNORECASE)
    structured["risk_score"] = risk_match.group(1) if risk_match else "0"

    # Problem 2: attack_type
    # Look for "Attack Type: <value>" on a single line (stop at newline)
    attack_match = re.search(r'Attack\s+Type[:\s]+(.+)', content, re.IGNORECASE)
    if attack_match:
        attack_type = attack_match.group(1).strip()
    else:
        # Fallback patterns
        attack_match = (
            re.search(r'attack.?pattern[:\s*]+([^\n]+)', content, re.IGNORECASE) or
            re.search(r'type of attack[:\s*]+([^\n]+)', content, re.IGNORECASE) or
            re.search(r'(brute force|sql injection|port scan|ddos|web scan)', content, re.IGNORECASE)
        )
        attack_type = attack_match.group(1).strip() if attack_match else "Multi-Vector Attack"
    # Clean up the result — remove markdown asterisks and trim
    attack_type = re.sub(r'\*+', '', attack_type).strip()
    # If too long (sentence), truncate to first meaningful phrase
    if len(attack_type) > 50:
        attack_type = attack_type[:50].split('.')[0].strip()
    structured["attack_type"] = attack_type

    # Problem 3: incident_id
    id_match = re.search(r'INC[-–][\w\-]+', content, re.IGNORECASE)
    if not id_match:
        # Generate from date in report
        date_match = re.search(r'Date[:\s]+(.+)', content, re.IGNORECASE)
        structured["incident_id"] = f"INC-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    else:
        structured["incident_id"] = id_match.group(0)

    # Problem 4: severity
    severity_match = (
        re.search(r'severity[:\s*]+([A-Z]+)', content, re.IGNORECASE) or
        re.search(r'risk.?level[:\s*]+([A-Z]+)', content, re.IGNORECASE) or
        re.search(r'(CRITICAL|HIGH|MEDIUM|LOW)\s+SEVERITY', content, re.IGNORECASE)
    )
    if severity_match:
        severity = severity_match.group(1).upper().strip()
        # Normalize
        if severity in ['HIGH', 'CRITICAL', 'MEDIUM', 'LOW']:
            pass
        elif 'CRITICAL' in content.upper():
            severity = 'CRITICAL'
        elif 'HIGH' in content.upper():
            severity = 'HIGH'
        else:
            severity = 'MEDIUM'
    else:
        severity = 'MEDIUM'
    structured["severity"] = severity

    # Problem 5: source_ip
    ip_match = (
        re.search(r'source.?ip[:\s*]+([\d\.]+)', content, re.IGNORECASE) or
        re.search(r'malicious.?ip[:\s*]+([\d\.]+)', content, re.IGNORECASE) or
        re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', content)
    )
    structured["source_ip"] = ip_match.group(1) if ip_match else None

    # Evidence
    evidence_match = re.search(r"(?is)^(?:#+\s*)?evidence.*?\n(.*?)(?:\n\s*#+|\Z)", content, re.MULTILINE)
    if evidence_match:
        structured["evidence"] = evidence_match.group(1).strip()
    else:
        tech_match = re.search(r"(?is)^(?:#+\s*)?technical\s*details.*?\n(.*?)(?:\n\s*#+|\Z)", content, re.MULTILINE)
        if tech_match:
            structured["evidence"] = tech_match.group(1).strip()

    # Recommended actions
    actions_match = re.search(r"(?is)^(?:#+\s*)?(recommended\s*actions|remediation|containment\s*&\s*remediation).*?\n(.*?)(?:\n\s*#+|\Z)", content, re.MULTILINE)
    if actions_match:
        actions_block = actions_match.group(2)
        actions = [
            re.sub(r"^[\-\*\d\.)\s]+", "", line).strip()
            for line in actions_block.splitlines()
            if line.strip().startswith(("-", "*", "1.", "2.", "3."))
        ]
        structured["recommended_actions"] = [a for a in actions if a]

    # Agent notes
    notes = re.findall(r"^\s*\[(\w+)\]\s*[:\-]?\s*(.+)$", content, re.MULTILINE)
    if notes:
        structured["agent_notes"] = [{"agent": a, "note": t.strip()} for a, t in notes]

    # Timeline
    timeline = re.findall(r"^\s*(\d{2}:\d{2}:\d{2})\s*[-–]\s*(.+)$", content, re.MULTILINE)
    if timeline:
        structured["timeline"] = [{"time": t, "event": e.strip()} for t, e in timeline]

    return structured

# Quick test with sample content
test_content = """
### Risk Assessment
- **Base Score:** 50
- **Total Risk Score:** 80
- **Risk Level:** HIGH SEVERITY
- **Malicious IP:** 192.168.1.55
Attack Pattern: Brute Force
"""
test_result = _parse_report_md(test_content)
print(f"TEST risk_score: {test_result['risk_score']}")  # should print 80
print(f"TEST severity: {test_result['severity']}")      # should print HIGH
print(f"TEST attack_type: {test_result['attack_type']}") # should print Brute Force
print(f"TEST source_ip: {test_result['source_ip']}")    # should print 192.168.1.55


@app.get("/report/structured")
def get_report_structured(path: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    global _session_active, _current_structured_report

    print("\n=== /report/structured called ===")
    print(f"_session_active = {_session_active}")
    print(f"_current_structured_report is None: {_current_structured_report is None}")

    report_path = path or os.path.join(CURRENT_DIR, "incident_report.md")
    result = {}

    # First try to read from file
    if os.path.exists(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"=== File exists, length = {len(content)} chars ===")
            if len(content) > 0:
                print(f"=== First 200 chars: {content[:200]} ===")
                result = _parse_report_md(content)
                print(f"=== Parsed risk_score: {result.get('risk_score')} ===")
                print(f"=== Parsed severity: {result.get('severity')} ===")
                print(f"=== Parsed attack_type: {result.get('attack_type')} ===")
            else:
                print("=== File exists but is EMPTY ===")
        except Exception as e:
            import traceback
            print(f"Error parsing structured report: {e}")
            traceback.print_exc()
    else:
        print(f"=== {report_path} does NOT exist ===")

    # Fall back to in-memory cached report
    if not result or result.get("risk_score") == "0":
        if _current_structured_report:
            print("=== Using cached _current_structured_report ===")
            result = _current_structured_report

    print(f"=== Final result keys: {list(result.keys()) if result else 'empty'} ===")
    return result

@app.post("/reset-session")
async def reset_session(current_user: dict = Depends(get_current_user)):
    """Reset the current session state and cleanup local files."""
    global _status, _session_active, _current_incident_md, _current_structured_report, anomaly_context
    _status = "idle"
    _session_active = False
    set_log_session_active(False)
    unlock_csv()
    _current_incident_md = None
    _current_structured_report = None
    anomaly_context = None
    os.environ.pop("ANOMALY_CONTEXT", None)
    
    # Cleanup local files
    for filename in ["incident_report.md", "data/simulation_logs.csv"]:
        path = get_data_file_path(filename)
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass
                
    return {"message": "Session reset successfully"}


# ──────────────────────────────────────────────────────────────────────────────
# Auth Endpoints (MongoDB-backed)
# ──────────────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleAuthRequest(BaseModel):
    token: str


@app.post("/auth/register")
async def register(req: RegisterRequest):
    try:
        await create_user_in_db(name=req.name, email=req.email, password=req.password)
        return {"message": "Account created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.post("/auth/login")
async def login(req: LoginRequest):
    user = await authenticate_user_in_db(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    user_id_str = str(user["_id"])
    access_token = create_access_token(data={"sub": user["email"], "user_id": user_id_str})
    await save_session(user_id=user_id_str, token=access_token)
    # Track active session for dynamic email alerts
    register_session(user_id_str, user["email"], user.get("name", ""))
    return {
        "token": access_token,
        "name": user["name"],
        "email": user["email"],
        "role": user.get("role", "analyst"),
        "profilePicture": user.get("profilePicture", ""),
        "authProvider": user.get("authProvider", "local"),
    }


# Keep legacy endpoints for backward compatibility
@app.post("/auth/signup")
async def signup(req: RegisterRequest):
    return await register(req)

@app.post("/auth/signin")
async def signin(req: LoginRequest):
    return await login(req)


@app.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_user), token: str = Depends(oauth2_scheme)):
    await delete_session(token)
    # Remove from active sessions so they stop receiving alert emails
    unregister_session(current_user.get("id", ""))
    return {"message": "Logged out successfully"}


@app.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@app.post("/auth/google")
async def google_auth(req: GoogleAuthRequest):
    """Authenticate via Google OAuth. Verifies the ID token, creates/updates the user, and returns a JWT."""
    try:
        google_info = await verify_google_token(req.token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception:
        raise HTTPException(status_code=401, detail="Google token verification failed")

    try:
        user = await google_login_or_create(google_info)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database unavailable")

    user_id_str = str(user["_id"])
    access_token = create_access_token(data={"sub": user["email"], "user_id": user_id_str})
    await save_session(user_id=user_id_str, token=access_token)
    # Track active session for dynamic email alerts
    register_session(user_id_str, user.get("email", ""), user.get("name", ""))

    return {
        "token": access_token,
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "analyst"),
        "profilePicture": user.get("profilePicture", ""),
        "authProvider": "google",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Incidents & Logs Endpoints (MongoDB)
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/incidents")
async def get_incidents(current_user: dict = Depends(get_current_user)):
    """Fetch all past incidents sorted by timestamp descending."""
    if db_module.incidents_collection is None:
        return []
    cursor = db_module.incidents_collection.find().sort("timestamp", -1)
    results = []
    async for doc in cursor:
        results.append(_serialize_doc(doc))
    return results


@app.get("/incidents/{incident_id}")
async def get_incident(incident_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch one incident by incident_id field."""
    if db_module.incidents_collection is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    doc = await db_module.incidents_collection.find_one({"incident_id": incident_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _serialize_doc(doc)


@app.delete("/incidents/{incident_id}")
async def delete_incident(incident_id: str, current_user: dict = Depends(get_current_user)):
    """Delete one incident (admin only)."""
    if db_module.incidents_collection is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    result = await db_module.incidents_collection.delete_one({"incident_id": incident_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"message": f"Incident {incident_id} deleted"}


@app.get("/db-logs")
async def get_db_logs(limit: int = 100, current_user: dict = Depends(get_current_user)):
    """Fetch last N log entries from MongoDB logs collection."""
    if db_module.logs_collection is None:
        return []
    cursor = db_module.logs_collection.find().sort("_id", -1).limit(limit)
    results = []
    async for doc in cursor:
        results.append(_serialize_doc(doc))
    return results


# ──────────────────────────────────────────────────────────────────────────────
# SSE stream — live log rows from tail_watcher
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/stream")
async def stream_logs():
    """Server-Sent Events endpoint streaming new log rows in real time."""
    q = subscribe()
    event_id = 0

    async def event_generator():
        nonlocal event_id
        try:
            while True:
                try:
                    row = await asyncio.wait_for(q.get(), timeout=30.0)
                    event_id += 1
                    print(f"=== /stream SSE: sending event #{event_id}, source={row.get('source_log', 'unknown')} ===")
                    yield {
                        "event": "message",
                        "id": str(row.get("id", event_id)),
                        "retry": 3000,
                        "data": json.dumps({"type": "log", "data": row, "id": row.get("id", event_id)}),
                    }
                except asyncio.TimeoutError:
                    yield {"comment": "keepalive"}
        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe(q)

    return EventSourceResponse(event_generator())


@app.get("/stream/replay")
async def stream_replay(limit: int = 100):
    """Return last N events from the replay buffer as an SSE burst for reconnection catch-up."""
    limit = min(limit, 10000)
    items = list(replay_buffer)[-limit:]

    async def replay_generator():
        for row in items:
            yield {
                "event": "message",
                "id": str(row.get("id", 0)),
                "data": json.dumps({"type": "log", "data": row, "id": row.get("id", 0)}),
            }

    return EventSourceResponse(replay_generator())


@app.get("/agent-feed")
async def agent_feed():
    """SSE stream for agent messages."""
    q = subscribe_agent()

    async def event_generator():
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield {
                        "event": "agent",
                        "id": str(msg.get("id", "")),
                        "retry": 3000,
                        "data": json.dumps(msg),
                    }
                except asyncio.TimeoutError:
                    yield {"comment": "keepalive"}
        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe_agent(q)

    return EventSourceResponse(event_generator())


@app.get("/agent-messages")
def get_agent_messages():
    """Return history of agent messages."""
    return {"messages": get_agent_messages_history()}


@app.get("/vulnlab-feed")
def vulnlab_feed():
    """Return recent VulnLab access log entries."""
    import log_watcher as lw
    return {
        "entries": lw._vulnlab_entries[-20:],
        "total": len(lw._vulnlab_entries),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Auto-Response Engine endpoints
# ──────────────────────────────────────────────────────────────────────────────

class AutoRespondRequest(BaseModel):
    dry_run: bool = True


@app.post("/auto-respond")
def trigger_auto_respond(body: AutoRespondRequest):
    """Manually trigger auto-response with configurable dry_run flag."""
    report_path = get_data_file_path("incident_report.md")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="No incident report found")
    with open(report_path, "r", encoding="utf-8") as f:
        md = f.read()
    structured = _parse_report_md(md)
    actions = execute_response(structured, dry_run=body.dry_run)
    return {"actions": actions}


@app.get("/response-audit")
def get_response_audit():
    """Return the full auto-response audit log."""
    return get_audit_log()


# ──────────────────────────────────────────────────────────────────────────────
# Threshold Engine & Alerts endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/thresholds")
def get_thresholds():
    """Return current threshold configuration."""
    return threshold_engine.get_thresholds().model_dump()


@app.put("/thresholds")
def update_thresholds(config: ThresholdConfig):
    """Update and hot-reload threshold configuration."""
    threshold_engine.update_thresholds(config)
    return {"status": "updated", "thresholds": config.model_dump()}


@app.get("/alerts")
def get_alerts(limit: int = 500):
    """Return last N alerts."""
    return threshold_engine.get_alerts(limit=limit)


@app.get("/alerts/live")
async def alerts_live():
    """Server-Sent Events stream of new alerts as they fire."""
    q = subscribe_alerts()

    async def alert_generator():
        try:
            while True:
                try:
                    alert_dict = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield {
                        "event": "alert",
                        "id": alert_dict.get("id", ""),
                        "retry": 3000,
                        "data": json.dumps(alert_dict, default=str),
                    }
                except asyncio.TimeoutError:
                    yield {"comment": "keepalive"}
        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe_alerts(q)

    return EventSourceResponse(alert_generator())


# ──────────────────────────────────────────────────────────────────────────────
# SMTP Email Alerting endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/smtp-status")
def smtp_status():
    """Return SMTP configuration status."""
    return alert_mailer.status()


@app.post("/test-email")
async def test_email():
    """Send a test alert email."""
    result = await alert_mailer.test_connection()
    return result


@app.get("/alert-email-status")
async def alert_email_status():
    """Return current alert email routing information."""
    return {
        "smtp_enabled": alert_mailer.enabled,
        "smtp_configured": alert_mailer.configured,
        "active_users": len(_active_sessions),
        "will_send_to": get_active_emails(),
        "fallback_recipients": alert_mailer.recipients,
        "last_sent": alert_mailer._last_sent,
    }

# ──────────────────────────────────────────────────────────────────────────────
# Port Scanner endpoints
# ──────────────────────────────────────────────────────────────────────────────

class ScanPortsRequest(BaseModel):
    target: str = "localhost"
    ports: str = "22,80,443,3306,5432,6379,8080,27017"


@app.post("/scan-ports")
async def scan_ports(body: ScanPortsRequest = ScanPortsRequest()):
    """Trigger an immediate nmap port scan."""
    return await port_scanner.scan(target=body.target, ports=body.ports)


@app.get("/port-scan-history")
def port_scan_history(limit: int = 10):
    """Return last N port scan results."""
    return port_scanner.get_history(limit=limit)


class AllowedPortsRequest(BaseModel):
    ports: List[int]


@app.put("/allowed-ports")
def update_allowed_ports(body: AllowedPortsRequest):
    """Update the allowed ports allowlist."""
    port_scanner.update_allowed(body.ports)
    return {"status": "updated", "allowed_ports": port_scanner.get_allowed()}


# ──────────────────────────────────────────────────────────────────────────────
# Blocked IPs endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/blocked-ips")
def get_blocked_ips_endpoint(
    current_user: dict = Depends(get_current_user)
):
    """Return list of currently blocked IPs."""
    from auto_responder import get_blocked_ips
    return {"blocked_ips": get_blocked_ips()}


@app.post("/unblock-ip")
async def unblock_ip_endpoint(
    body: dict,
    current_user: dict = Depends(get_current_user)
):
    """Unblock a specific IP address."""
    ip = body.get("ip")
    if not ip:
        raise HTTPException(status_code=400, detail="IP required")
    from auto_responder import unblock_ip
    result = unblock_ip(ip)
    return result


@app.post("/block-ip")
async def block_ip_endpoint(
    body: dict,
    current_user: dict = Depends(get_current_user)
):
    """Manually block a specific IP address."""
    ip = body.get("ip")
    if not ip:
        raise HTTPException(status_code=400, detail="IP required")
    from auto_responder import block_ip
    result = block_ip(ip)
    return result
