"""
Live Log Ingestor — watches system logs and appends parsed rows to simulation_logs.csv.

Supports:
  - Linux/Mac: tail -F /var/log/auth.log
  - Windows: Windows Event Log (Security, Event IDs 4624/4625/4648) via pywin32
  - Fallback: watches WATCH_LOG_PATH from .env, or generates synthetic logs
"""

import asyncio
import csv
import io
import json
import logging
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).parent
DATA_DIR = BACKEND_DIR / "data"
CSV_PATH = DATA_DIR / "simulation_logs.csv"
CSV_FIELDS = ["timestamp", "ip_address", "user", "status", "endpoint"]

# Global broadcast queue: SSE subscribers listen here
_subscribers: List[asyncio.Queue] = []


def subscribe() -> asyncio.Queue:
    """Create a new subscriber queue for SSE streaming."""
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    """Remove a subscriber queue."""
    try:
        _subscribers.remove(q)
    except ValueError:
        pass


def _broadcast(row: Dict[str, str]) -> None:
    """Push a row dict to all subscriber queues."""
    for q in _subscribers:
        try:
            q.put_nowait(row)
        except asyncio.QueueFull:
            pass  # drop if consumer is too slow


def _ensure_csv() -> None:
    """Ensure the CSV file exists with a header row."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()


def _append_row(row: Dict[str, str]) -> None:
    """Append a single parsed row to the CSV and flush immediately."""
    _ensure_csv()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writerow(row)
        f.flush()


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

_IP_RE = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
_USER_RE = re.compile(r"(?:for|user|by)\s+(\w+)", re.IGNORECASE)


def parse_auth_log_line(line: str) -> Optional[Dict[str, str]]:
    """Parse a single auth.log line into the CSV schema."""
    line = line.strip()
    if not line:
        return None

    ip_match = _IP_RE.search(line)
    ip = ip_match.group(1) if ip_match else "0.0.0.0"

    user_match = _USER_RE.search(line)
    user = user_match.group(1) if user_match else "unknown"

    lower = line.lower()
    if "failed" in lower or "failure" in lower or "invalid" in lower:
        status = "Failed_Login"
    elif "accepted" in lower or "opened" in lower or "success" in lower:
        status = "Success_Login"
    else:
        return None  # skip non-auth lines

    # Try to extract timestamp from syslog format (e.g. "Mar 14 08:30:01")
    ts_match = re.match(r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})", line)
    if ts_match:
        try:
            raw_ts = ts_match.group(1)
            year = datetime.now().year
            dt = datetime.strptime(f"{year} {raw_ts}", "%Y %b %d %H:%M:%S")
            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "timestamp": timestamp,
        "ip_address": ip,
        "user": user,
        "status": status,
        "endpoint": "/ssh",
    }


def parse_windows_event(event_id: int, data: dict) -> Optional[Dict[str, str]]:
    """Parse a Windows Security event into the CSV schema."""
    if event_id == 4625:
        status = "Failed_Login"
    elif event_id in (4624, 4648):
        status = "Success_Login"
    else:
        return None

    ip = data.get("IpAddress") or "0.0.0.0"
    if ip in ("-", ""):
        ip = "0.0.0.0"
    user = data.get("TargetUserName") or data.get("SubjectUserName") or "unknown"
    timestamp = data.get("TimeCreated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    return {
        "timestamp": timestamp,
        "ip_address": ip,
        "user": user,
        "status": status,
        "endpoint": "/winlogon",
    }


# ---------------------------------------------------------------------------
# Watchers
# ---------------------------------------------------------------------------

async def _watch_auth_log(path: str = "/var/log/auth.log") -> None:
    """Use tail -F to follow the auth log on Linux/Mac."""
    logger.info("tail_watcher: following %s", path)
    proc = await asyncio.create_subprocess_exec(
        "tail", "-F", "-n", "0", path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert proc.stdout is not None
    try:
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace")
            row = parse_auth_log_line(line)
            if row:
                _append_row(row)
                _broadcast(row)
    except asyncio.CancelledError:
        proc.kill()
        raise
    finally:
        proc.kill()


async def _watch_windows_events() -> None:
    """Poll Windows Security Event Log for logon events."""
    try:
        import win32evtlog  # type: ignore
        import win32evtlogutil  # type: ignore
    except ImportError:
        logger.warning("pywin32 not available — cannot watch Windows Event Log")
        raise

    server = "localhost"
    log_type = "Security"
    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
    handle = win32evtlog.OpenEventLog(server, log_type)

    # Track the last record number we've seen
    last_record = win32evtlog.GetNumberOfEventLogRecords(handle)

    target_ids = {4624, 4625, 4648}

    while True:
        await asyncio.sleep(2)
        try:
            events = win32evtlog.ReadEventLog(handle, flags, 0)
            for event in events:
                if event.EventID & 0xFFFF not in target_ids:
                    continue
                eid = event.EventID & 0xFFFF
                data = {}
                if event.StringInserts:
                    strings = event.StringInserts
                    data["TargetUserName"] = strings[5] if len(strings) > 5 else "unknown"
                    data["IpAddress"] = strings[18] if len(strings) > 18 else "0.0.0.0"
                data["TimeCreated"] = event.TimeGenerated.Format("%Y-%m-%d %H:%M:%S")
                row = parse_windows_event(eid, data)
                if row:
                    _append_row(row)
                    _broadcast(row)
        except Exception as e:
            logger.debug("Windows event read error: %s", e)
            await asyncio.sleep(5)


async def _watch_file(path: str) -> None:
    """Tail a generic log file, attempting auth.log-style parsing."""
    logger.info("tail_watcher: watching file %s", path)
    if not os.path.exists(path):
        logger.warning("Watch path %s does not exist yet — waiting...", path)
        while not os.path.exists(path):
            await asyncio.sleep(2)

    # Open file and seek to end
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(0, 2)  # seek to end
        while True:
            line = f.readline()
            if line:
                row = parse_auth_log_line(line)
                if row:
                    _append_row(row)
                    _broadcast(row)
            else:
                await asyncio.sleep(0.5)


async def _generate_synthetic_logs() -> None:
    """
    Fallback: generate synthetic log rows periodically using logic from
    generate_chaos_logs.py so the system always has data flowing.
    """
    import random

    logger.info("tail_watcher: generating synthetic logs (fallback mode)")

    normal_ips = [f"10.0.0.{i}" for i in range(1, 20)]
    attacker_ips = ["192.168.1.55", "45.33.22.11", "203.0.113.8"]
    users = ["alice", "bob", "charlie", "david", "eve", "frank", "grace", "heidi"]
    endpoints = ["/home", "/about", "/products", "/contact", "/login", "/dashboard", "/api/user"]
    attack_endpoints = ["/admin/login", "/wp-admin", "/.env", "/phpmyadmin"]

    while True:
        await asyncio.sleep(random.uniform(3, 10))

        # 80% normal traffic, 20% suspicious
        if random.random() < 0.8:
            row = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ip_address": random.choice(normal_ips),
                "user": random.choice(users),
                "status": "Success",
                "endpoint": random.choice(endpoints),
            }
        else:
            is_brute = random.random() < 0.5
            row = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ip_address": random.choice(attacker_ips),
                "user": "admin" if is_brute else "unknown",
                "status": "Failed_Login" if is_brute else "404_Not_Found",
                "endpoint": "/admin/login" if is_brute else random.choice(attack_endpoints),
            }

        _append_row(row)
        _broadcast(row)


# ---------------------------------------------------------------------------
# Entry point — called from server.py lifespan
# ---------------------------------------------------------------------------

async def start_watcher() -> None:
    """
    Detect OS and available log sources, then start the appropriate watcher.
    Priority:
      1. Linux/Mac auth.log
      2. Windows Event Log
      3. WATCH_LOG_PATH from env
      4. Synthetic log generation (fallback)
    """
    _ensure_csv()
    system = platform.system().lower()

    # 1. Linux / Mac — try auth.log
    if system in ("linux", "darwin"):
        auth_path = "/var/log/auth.log"
        if system == "darwin":
            auth_path = "/var/log/system.log"
        if os.path.exists(auth_path) and os.access(auth_path, os.R_OK):
            await _watch_auth_log(auth_path)
            return

    # 2. Windows — try Event Log
    if system == "windows":
        try:
            await _watch_windows_events()
            return
        except Exception:
            logger.info("Windows Event Log not available, trying fallback...")

    # 3. WATCH_LOG_PATH from .env
    watch_path = os.environ.get("WATCH_LOG_PATH", "").strip()
    if watch_path:
        await _watch_file(watch_path)
        return

    # 4. Fallback — synthetic logs
    await _generate_synthetic_logs()
