"""
Multi-Source Log Watcher — monitors multiple system log files simultaneously,
parses each line into a unified schema, appends to CSV, and broadcasts via queues.

Supported sources:
  Linux:
    - /var/log/auth.log         (SSH failures, sudo, SSH keys)
    - /var/log/ufw.log          (firewall blocks)
    - /var/log/nginx/access.log (SQLi, 4xx/5xx, path traversal)
    - /var/log/audit/audit.log  (file access on sensitive paths)
    - /var/log/dhcpd.log        (rogue device assignments)
    - /var/log/pihole.log or /var/log/named/default (DNS anomalies)
    - /var/log/syslog           (general fallback)

  Windows:
    - Windows Security Event Log (Event IDs 4624, 4625, 4648, 4672)
    - Windows Firewall log (pfirewall.log)
    - Active network connections via netstat
    - FastAPI/uvicorn access logs (injected from middleware)

  Fallback:
    - WATCH_LOG_PATH from .env  (user-specified fallback)
    - Synthetic generation      (ultimate fallback)

Architecture:
  - watchdog.Observer watches directories for file modifications (thread-based)
  - asyncio.run_coroutine_threadsafe bridges into the event loop
  - Parsed rows are appended to CSV, pushed to asyncio queues, and stored in deque
  - GeoIP enrichment via ip-api.com (cached, rate-limited)
"""

import asyncio
import collections
import csv
import json
import logging
import os
import platform
import re
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"

if os.environ.get("IS_VERCEL") == "true":
    DATA_DIR = Path("/tmp/data")
    CSV_PATH = DATA_DIR / "simulation_logs.csv"
else:
    BACKEND_DIR = Path(__file__).parent
    DATA_DIR = BACKEND_DIR / "data"
    CSV_PATH = DATA_DIR / "simulation_logs.csv"
CSV_FIELDS = ["timestamp", "ip_address", "user", "status", "endpoint"]

# Extended fields for SSE/frontend (not written to CSV for agent compat)
EXTENDED_FIELDS = CSV_FIELDS + ["source_log", "raw_line", "country", "city"]

# In-memory replay buffer (last 10,000 events)
replay_buffer: Deque[Dict[str, Any]] = collections.deque(maxlen=10000)

# Subscriber queues for SSE streaming
_subscribers: List[asyncio.Queue] = []
_subscribers_lock = threading.Lock()

# Alert subscriber queues (separate channel for threshold alerts)
_alert_subscribers: List[asyncio.Queue] = []
_alert_subscribers_lock = threading.Lock()

# Agent message subscriber queues
_agent_subscribers: List[asyncio.Queue] = []
_agent_subscribers_lock = threading.Lock()
_agent_messages_history: Deque[Dict[str, Any]] = collections.deque(maxlen=1000)

# GeoIP cache: ip -> {"country": ..., "city": ...}
_geoip_cache: Dict[str, Dict[str, str]] = {}
_geoip_lock = threading.Lock()

# Event loop reference for thread->async bridging
_loop: Optional[asyncio.AbstractEventLoop] = None

# Callback for threshold evaluation (set by server.py)
_on_new_row: Optional[Callable] = None

# Session gate — if False, we skip CSV writes (but live monitor still works)
_is_session_active: bool = False
_csv_locked: bool = False

# Live monitor mode — always True once watcher starts, allows SSE broadcast
# even when no CSV upload/simulation session is active
_live_monitor_active: bool = False

def set_session_active(state: bool) -> None:
    global _is_session_active
    print(f"log_watcher: session state changed to {state}")
    _is_session_active = state
    if not state:
        replay_buffer.clear()

def set_live_monitor(state: bool) -> None:
    """Enable/disable the always-on live monitor mode."""
    global _live_monitor_active
    _live_monitor_active = state
    print(f"log_watcher: live monitor {'enabled' if state else 'disabled'}")

def lock_csv():
    """Call this when user uploads CSV — stops synthetic generator from writing to it"""
    global _csv_locked
    _csv_locked = True
    print("log_watcher: CSV locked — synthetic generator will not write to simulation_logs.csv")

def unlock_csv():
    """Call this on reset — allows fresh CSV uploads"""
    global _csv_locked
    _csv_locked = False
    print("log_watcher: CSV unlocked")



def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def set_on_new_row(callback: Callable) -> None:
    """Register a callback that is called for every new log row (for threshold engine)."""
    global _on_new_row
    _on_new_row = callback


# ---------------------------------------------------------------------------
# Subscriber management
# ---------------------------------------------------------------------------

def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    with _subscribers_lock:
        _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    with _subscribers_lock:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass


def subscribe_alerts() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    with _alert_subscribers_lock:
        _alert_subscribers.append(q)
    return q


def unsubscribe_alerts(q: asyncio.Queue) -> None:
    with _alert_subscribers_lock:
        try:
            _alert_subscribers.remove(q)
        except ValueError:
            pass


def subscribe_agent() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    with _agent_subscribers_lock:
        _agent_subscribers.append(q)
    return q


def unsubscribe_agent(q: asyncio.Queue) -> None:
    with _agent_subscribers_lock:
        try:
            _agent_subscribers.remove(q)
        except ValueError:
            pass


def broadcast_agent_message(agent: str, message: str, type: str = "info") -> None:
    """Push an agent message to all agent subscriber queues and history."""
    msg_dict = {
        "id": int(time.time() * 1000),
        "agent": agent,
        "message": message,
        "type": type,
        "timestamp": datetime.now().isoformat(),
    }
    _agent_messages_history.append(msg_dict)
    with _agent_subscribers_lock:
        for q in _agent_subscribers:
            try:
                q.put_nowait(msg_dict)
            except asyncio.QueueFull:
                pass


def get_agent_messages_history() -> List[Dict[str, Any]]:
    return list(_agent_messages_history)


def broadcast_alert(alert_dict: Dict) -> None:
    """Push an alert to all alert subscriber queues."""
    with _alert_subscribers_lock:
        for q in _alert_subscribers:
            try:
                q.put_nowait(alert_dict)
            except asyncio.QueueFull:
                pass


def _broadcast(row: Dict[str, Any]) -> None:
    """Push a row to all log subscriber queues (thread-safe)."""
    with _subscribers_lock:
        for q in _subscribers:
            try:
                q.put_nowait(row)
            except asyncio.QueueFull:
                pass


# ---------------------------------------------------------------------------
# CSV operations
# ---------------------------------------------------------------------------

def _ensure_csv() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()


def _append_csv(row: Dict[str, str]) -> None:
    """Append a row to CSV (only the 5 standard columns for agent compat)."""
    _ensure_csv()
    csv_row = {k: row.get(k, "") for k in CSV_FIELDS}
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writerow(csv_row)
        f.flush()


# ---------------------------------------------------------------------------
# GeoIP enrichment via ip-api.com (free, rate-limited 45/min)
# ---------------------------------------------------------------------------

def _geoip_lookup(ip: str) -> Dict[str, str]:
    """Look up GeoIP data, returning cached results when available."""
    if ip in ("0.0.0.0", "127.0.0.1", "-") or ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172."):
        return {"country": "Private", "city": "LAN"}

    with _geoip_lock:
        if ip in _geoip_cache:
            return _geoip_cache[ip]

    try:
        import httpx
        resp = httpx.get(f"http://ip-api.com/json/{ip}?fields=country,city", timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            result = {
                "country": data.get("country", "Unknown"),
                "city": data.get("city", "Unknown"),
            }
        else:
            result = {"country": "Unknown", "city": "Unknown"}
    except Exception:
        result = {"country": "Unknown", "city": "Unknown"}

    with _geoip_lock:
        _geoip_cache[ip] = result
    return result


# ---------------------------------------------------------------------------
# Process a parsed row through the full pipeline
# ---------------------------------------------------------------------------

_event_counter = 0
_event_counter_lock = threading.Lock()


def _process_row(row: Dict[str, Any]) -> None:
    """Central pipeline: CSV append → GeoIP enrich → deque → broadcast → Redis → threshold callback.

    Rows are ALWAYS processed when live_monitor is active (for real-time SSE).
    CSV writes only happen when a session is active and CSV is not locked.
    """
    global _event_counter, _is_session_active, _csv_locked, _live_monitor_active

    # Gate: must have either a session or live monitor active
    if not _is_session_active and not _live_monitor_active:
        return

    # Enrich with GeoIP
    ip = row.get("ip_address", "0.0.0.0")
    geo = _geoip_lookup(ip)
    row["country"] = geo["country"]
    row["city"] = geo["city"]

    # Assign event ID
    with _event_counter_lock:
        _event_counter += 1
        row["id"] = _event_counter

    # Append to CSV only during active session (not for always-on live monitor)
    if _is_session_active and not _csv_locked:
        _append_csv(row)

    # Store in replay buffer
    replay_buffer.append(row)

    # Broadcast to SSE subscribers
    _broadcast(row)

    # Publish to Redis (non-blocking, fire-and-forget)
    try:
        from redis_pipeline import publisher as _redis_pub
        if _redis_pub.available:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(_redis_pub.publish(row), loop)
    except Exception:
        pass  # graceful — Redis is optional

    # Call threshold engine callback if registered
    if _on_new_row is not None:
        try:
            _on_new_row(row)
        except Exception as e:
            logger.debug("Threshold callback error: %s", e)


def inject_access_log(method: str, path: str, status_code: int, client_ip: str, user: str = "unknown") -> None:
    """Called from FastAPI middleware to feed uvicorn/access log events into the pipeline."""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    status = "Success"
    if status_code == 404:
        status = "404_Not_Found"
    elif status_code >= 500:
        status = "500_Server_Error"
    elif status_code == 403:
        status = "Blocked_Connection"
    elif status_code >= 400:
        status = "404_Not_Found"

    # Check for SQLi in path
    if _SQLI_RE.search(path):
        status = "SQL_Injection"

    row = {
        "timestamp": now,
        "ip_address": client_ip,
        "user": user,
        "status": status,
        "endpoint": f"{method} {path}"[:100],
        "source_log": "uvicorn/access",
        "raw_line": f"{client_ip} {method} {path} {status_code}",
    }
    _process_row(row)


# ---------------------------------------------------------------------------
# Parsers for each log source
# ---------------------------------------------------------------------------

_IP_RE = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
_SYSLOG_TS_RE = re.compile(r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})")
_SQLI_RE = re.compile(r"(?:union\s+select|or\s+1\s*=\s*1|drop\s+table|--|%27|xp_|/etc/passwd|\.\./)", re.IGNORECASE)


def _extract_syslog_ts(line: str) -> str:
    m = _SYSLOG_TS_RE.match(line)
    if m:
        try:
            year = datetime.now().year
            dt = datetime.strptime(f"{year} {m.group(1)}", "%Y %b %d %H:%M:%S")
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def parse_auth_log(line: str) -> Optional[Dict[str, Any]]:
    """Parse auth.log lines for SSH failures, sudo, accepted logins."""
    line_s = line.strip()
    if not line_s:
        return None

    lower = line_s.lower()
    ts = _extract_syslog_ts(line_s)
    ip_m = _IP_RE.search(line_s)
    ip = ip_m.group(1) if ip_m else "0.0.0.0"

    # SSH Failed password
    m = re.search(r"sshd.*Failed password for (\S+) from ([\d.]+)", line_s)
    if m:
        return {
            "timestamp": ts, "ip_address": m.group(2), "user": m.group(1),
            "status": "Failed_Login", "endpoint": "/ssh",
            "source_log": "auth.log", "raw_line": line_s[:200],
        }

    # SSH Accepted
    m = re.search(r"sshd.*Accepted\s+\S+\s+for\s+(\S+)\s+from\s+([\d.]+)", line_s)
    if m:
        return {
            "timestamp": ts, "ip_address": m.group(2), "user": m.group(1),
            "status": "Success_Login", "endpoint": "/ssh",
            "source_log": "auth.log", "raw_line": line_s[:200],
        }

    # Sudo usage
    m = re.search(r"sudo:\s*(\S+).*COMMAND=(.+)", line_s)
    if m:
        return {
            "timestamp": ts, "ip_address": ip, "user": m.group(1),
            "status": "Sudo_Escalation", "endpoint": m.group(2).strip()[:100],
            "source_log": "auth.log", "raw_line": line_s[:200],
        }

    # SSH key added
    if "authorized_keys" in lower or "ssh-rsa" in lower or "ssh-ed25519" in lower:
        user_m = re.search(r"for\s+(\S+)", line_s)
        return {
            "timestamp": ts, "ip_address": ip, "user": user_m.group(1) if user_m else "unknown",
            "status": "File_Access", "endpoint": "~/.ssh/authorized_keys",
            "source_log": "auth.log", "raw_line": line_s[:200],
        }

    # General failures
    if "failed" in lower or "failure" in lower or "invalid" in lower:
        user_m = re.search(r"(?:for|user|by)\s+(\w+)", line_s, re.IGNORECASE)
        return {
            "timestamp": ts, "ip_address": ip, "user": user_m.group(1) if user_m else "unknown",
            "status": "Failed_Login", "endpoint": "/ssh",
            "source_log": "auth.log", "raw_line": line_s[:200],
        }

    return None


def parse_ufw_log(line: str) -> Optional[Dict[str, Any]]:
    """Parse UFW firewall log lines."""
    line_s = line.strip()
    if not line_s:
        return None

    m = re.search(r"UFW BLOCK.*SRC=([\d.]+).*DPT=(\d+)", line_s)
    if m:
        ts = _extract_syslog_ts(line_s)
        return {
            "timestamp": ts, "ip_address": m.group(1), "user": "unknown",
            "status": "Blocked_Connection", "endpoint": f"port/{m.group(2)}",
            "source_log": "ufw.log", "raw_line": line_s[:200],
        }

    m = re.search(r"UFW ALLOW.*SRC=([\d.]+).*DPT=(\d+)", line_s)
    if m:
        ts = _extract_syslog_ts(line_s)
        return {
            "timestamp": ts, "ip_address": m.group(1), "user": "unknown",
            "status": "Success_Login", "endpoint": f"port/{m.group(2)}",
            "source_log": "ufw.log", "raw_line": line_s[:200],
        }
    return None


def parse_nginx_access(line: str) -> Optional[Dict[str, Any]]:
    """Parse nginx/apache combined log format."""
    line_s = line.strip()
    if not line_s:
        return None

    # Combined log: IP - user [timestamp] "METHOD URI HTTP/x" status size "referer" "ua"
    m = re.match(
        r'([\d.]+)\s+\S+\s+(\S+)\s+\[([^\]]+)\]\s+"(?:\S+)\s+(\S+)\s+[^"]*"\s+(\d+)',
        line_s,
    )
    if not m:
        return None

    ip, user, ts_raw, uri, status_code = m.group(1), m.group(2), m.group(3), m.group(4), int(m.group(5))

    # Parse nginx timestamp
    try:
        dt = datetime.strptime(ts_raw.split()[0], "%d/%b/%Y:%H:%M:%S")
        ts = dt.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    if user == "-":
        user = "unknown"

    # Check for SQLi patterns in URI
    if _SQLI_RE.search(uri):
        return {
            "timestamp": ts, "ip_address": ip, "user": user,
            "status": "SQL_Injection", "endpoint": uri[:100],
            "source_log": "nginx/access.log", "raw_line": line_s[:200],
        }

    if status_code == 404:
        return {
            "timestamp": ts, "ip_address": ip, "user": user,
            "status": "404_Not_Found", "endpoint": uri[:100],
            "source_log": "nginx/access.log", "raw_line": line_s[:200],
        }

    if status_code >= 500:
        return {
            "timestamp": ts, "ip_address": ip, "user": user,
            "status": "500_Server_Error", "endpoint": uri[:100],
            "source_log": "nginx/access.log", "raw_line": line_s[:200],
        }

    if status_code >= 400:
        return {
            "timestamp": ts, "ip_address": ip, "user": user,
            "status": "404_Not_Found", "endpoint": uri[:100],
            "source_log": "nginx/access.log", "raw_line": line_s[:200],
        }

    # Normal 2xx/3xx — still record for velocity tracking
    return {
        "timestamp": ts, "ip_address": ip, "user": user,
        "status": "Success", "endpoint": uri[:100],
        "source_log": "nginx/access.log", "raw_line": line_s[:200],
    }


def parse_audit_log(line: str) -> Optional[Dict[str, Any]]:
    """Parse auditd log for file access on sensitive paths."""
    line_s = line.strip()
    if not line_s:
        return None

    sensitive_paths = ("/etc/passwd", "/etc/shadow", "/.ssh", "/etc/sudoers")
    lower = line_s.lower()

    if not any(p in lower for p in sensitive_paths):
        return None

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    # Try to extract audit timestamp
    m = re.search(r"msg=audit\((\d+)\.\d+:", line_s)
    if m:
        try:
            ts = datetime.fromtimestamp(int(m.group(1))).strftime("%Y-%m-%dT%H:%M:%S")
        except (ValueError, OSError):
            pass

    user_m = re.search(r"uid=(\d+)", line_s)
    user = user_m.group(1) if user_m else "unknown"

    path_m = re.search(r'name="([^"]+)"', line_s)
    endpoint = path_m.group(1) if path_m else "sensitive_file"

    return {
        "timestamp": ts, "ip_address": "0.0.0.0", "user": user,
        "status": "File_Access", "endpoint": endpoint[:100],
        "source_log": "audit.log", "raw_line": line_s[:200],
    }


def parse_dhcp_log(line: str) -> Optional[Dict[str, Any]]:
    """Parse DHCP log for new device lease assignments."""
    line_s = line.strip()
    if not line_s:
        return None

    lower = line_s.lower()
    if "dhcpack" not in lower and "lease" not in lower and "discover" not in lower:
        return None

    ts = _extract_syslog_ts(line_s)
    ip_m = _IP_RE.search(line_s)
    ip = ip_m.group(1) if ip_m else "0.0.0.0"

    # Try to extract MAC
    mac_m = re.search(r"([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})", line_s)
    mac = mac_m.group(1) if mac_m else "unknown"

    return {
        "timestamp": ts, "ip_address": ip, "user": mac,
        "status": "Rogue_Device", "endpoint": "/dhcp",
        "source_log": "dhcpd.log", "raw_line": line_s[:200],
    }


def parse_dns_log(line: str) -> Optional[Dict[str, Any]]:
    """Parse DNS logs for anomalous queries."""
    line_s = line.strip()
    if not line_s:
        return None

    suspicious_tlds = (".xyz", ".tk", ".ml", ".ga", ".cf", ".top", ".buzz", ".club", ".icu")
    lower = line_s.lower()

    is_anomaly = False
    if "nxdomain" in lower:
        is_anomaly = True
    elif any(tld in lower for tld in suspicious_tlds):
        is_anomaly = True

    if not is_anomaly:
        return None

    ts = _extract_syslog_ts(line_s)
    ip_m = _IP_RE.search(line_s)
    ip = ip_m.group(1) if ip_m else "0.0.0.0"

    # Try to extract queried domain
    domain_m = re.search(r"query\[.*?\]\s+(\S+)", line_s) or re.search(r"(\S+\.\S+)", line_s)
    domain = domain_m.group(1) if domain_m else "unknown"

    return {
        "timestamp": ts, "ip_address": ip, "user": "unknown",
        "status": "DNS_Anomaly", "endpoint": domain[:100],
        "source_log": "dns.log", "raw_line": line_s[:200],
    }


def parse_syslog(line: str) -> Optional[Dict[str, Any]]:
    """Generic syslog parser — catches remaining auth/error events."""
    line_s = line.strip()
    if not line_s:
        return None

    lower = line_s.lower()
    ts = _extract_syslog_ts(line_s)
    ip_m = _IP_RE.search(line_s)
    ip = ip_m.group(1) if ip_m else "0.0.0.0"

    if "failed" in lower or "failure" in lower or "denied" in lower:
        user_m = re.search(r"(?:for|user|by)\s+(\w+)", line_s, re.IGNORECASE)
        return {
            "timestamp": ts, "ip_address": ip,
            "user": user_m.group(1) if user_m else "unknown",
            "status": "Failed_Login", "endpoint": "/syslog",
            "source_log": "syslog", "raw_line": line_s[:200],
        }

    if "error" in lower or "critical" in lower or "emergency" in lower:
        return {
            "timestamp": ts, "ip_address": ip, "user": "unknown",
            "status": "500_Server_Error", "endpoint": "/syslog",
            "source_log": "syslog", "raw_line": line_s[:200],
        }

    return None


# ---------------------------------------------------------------------------
# Windows-specific parsers
# ---------------------------------------------------------------------------

def parse_windows_firewall_log(line: str) -> Optional[Dict[str, Any]]:
    """Parse Windows Firewall log (pfirewall.log).

    Format: date time action protocol src-ip dst-ip src-port dst-port ...
    Example: 2024-01-15 10:30:45 DROP TCP 192.168.1.100 10.0.0.1 54321 443 ...
    """
    line_s = line.strip()
    if not line_s or line_s.startswith("#"):
        return None

    parts = line_s.split()
    if len(parts) < 8:
        return None

    try:
        date_str, time_str = parts[0], parts[1]
        action = parts[2].upper()
        protocol = parts[3].upper()
        src_ip = parts[4]
        dst_ip = parts[5]
        src_port = parts[6]
        dst_port = parts[7]
    except (IndexError, ValueError):
        return None

    # Validate IP format
    if not _IP_RE.match(src_ip):
        return None

    ts = f"{date_str}T{time_str}"

    if action == "DROP":
        return {
            "timestamp": ts, "ip_address": src_ip, "user": "unknown",
            "status": "Blocked_Connection",
            "endpoint": f"port/{dst_port} ({protocol})",
            "source_log": "windows_firewall", "raw_line": line_s[:200],
        }
    elif action == "ALLOW":
        return {
            "timestamp": ts, "ip_address": src_ip, "user": "unknown",
            "status": "Success",
            "endpoint": f"port/{dst_port} ({protocol})",
            "source_log": "windows_firewall", "raw_line": line_s[:200],
        }

    return None


def _parse_netstat_output(output: str) -> List[Dict[str, Any]]:
    """Parse netstat -an output into connection events."""
    rows = []
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    for line in output.splitlines():
        line_s = line.strip()
        if not line_s:
            continue

        # Match TCP/UDP lines: Proto  Local Address  Foreign Address  State
        m = re.match(
            r"(TCP|UDP)\s+([\d.]+):(\d+)\s+([\d.]+):(\d+)\s*(\S*)",
            line_s, re.IGNORECASE,
        )
        if not m:
            continue

        proto = m.group(1).upper()
        local_ip = m.group(2)
        local_port = m.group(3)
        remote_ip = m.group(4)
        remote_port = m.group(5)
        state = m.group(6) if m.group(6) else ""

        # Skip loopback and unresolved
        if remote_ip in ("0.0.0.0", "127.0.0.1", "*"):
            continue

        status = "Active_Connection"
        if state.upper() == "ESTABLISHED":
            status = "Active_Connection"
        elif state.upper() == "SYN_SENT":
            status = "Active_Connection"
        elif state.upper() in ("CLOSE_WAIT", "TIME_WAIT", "FIN_WAIT_2"):
            continue  # Skip closing connections to reduce noise

        rows.append({
            "timestamp": now,
            "ip_address": remote_ip,
            "user": "unknown",
            "status": status,
            "endpoint": f"port/{local_port} ({proto})",
            "source_log": "netstat",
            "raw_line": line_s[:200],
        })

    return rows


# ---------------------------------------------------------------------------
# Windows Event Log reader (pywin32)
# ---------------------------------------------------------------------------

# Event IDs we care about
_WIN_EVENT_IDS = {
    4624: ("Success_Login", "Successful logon"),
    4625: ("Failed_Login", "Failed logon attempt"),
    4648: ("Success_Login", "Explicit credential logon"),
    4672: ("Sudo_Escalation", "Admin/special privileges assigned"),
}


def _read_windows_event_log(last_record_number: int) -> tuple[List[Dict[str, Any]], int]:
    """Read new Security events from Windows Event Log using pywin32.

    Returns (list_of_parsed_rows, new_last_record_number).
    """
    rows = []
    new_last = last_record_number

    try:
        import win32evtlog
        import win32evtlogutil

        server = None  # local machine
        log_type = "Security"
        flags = win32evtlog.EVENTLOG_FORWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

        hand = win32evtlog.OpenEventLog(server, log_type)
        try:
            total = win32evtlog.GetNumberOfEventLogRecords(hand)

            while True:
                events = win32evtlog.ReadEventLog(hand, flags, 0)
                if not events:
                    break

                for event in events:
                    record_num = event.RecordNumber
                    if record_num <= last_record_number:
                        continue

                    new_last = max(new_last, record_num)
                    event_id = event.EventID & 0xFFFF  # Mask to get actual ID

                    if event_id not in _WIN_EVENT_IDS:
                        continue

                    status, description = _WIN_EVENT_IDS[event_id]

                    # Parse event time
                    try:
                        ts = event.TimeGenerated.Format("%Y-%m-%dT%H:%M:%S")
                    except Exception:
                        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                    # Extract IP and username from event data strings
                    ip = "127.0.0.1"
                    user = "unknown"
                    strings = event.StringInserts or []

                    if event_id in (4624, 4625):
                        # Strings[5] = TargetUserName, Strings[18] = IpAddress (4624)
                        # Strings[5] = TargetUserName, Strings[19] = IpAddress (4625)
                        if len(strings) > 5:
                            user = strings[5] or "unknown"
                        ip_idx = 18 if event_id == 4624 else 19
                        if len(strings) > ip_idx:
                            raw_ip = strings[ip_idx] or ""
                            if raw_ip and raw_ip != "-":
                                ip = raw_ip.strip()
                    elif event_id == 4648:
                        # Strings[1] = SubjectUserName, Strings[5] = TargetUserName
                        # Strings[12] = IpAddress
                        if len(strings) > 5:
                            user = strings[5] or "unknown"
                        if len(strings) > 12:
                            raw_ip = strings[12] or ""
                            if raw_ip and raw_ip != "-":
                                ip = raw_ip.strip()
                    elif event_id == 4672:
                        # Strings[1] = SubjectUserName
                        if len(strings) > 1:
                            user = strings[1] or "unknown"

                    # Clean up IPv6 loopback
                    if ip in ("::", "::1", "-", ""):
                        ip = "127.0.0.1"

                    row = {
                        "timestamp": ts,
                        "ip_address": ip,
                        "user": user,
                        "status": status,
                        "endpoint": f"/event/{event_id} ({description})",
                        "source_log": "windows_security",
                        "raw_line": f"EventID={event_id} User={user} IP={ip}",
                    }
                    rows.append(row)

        finally:
            win32evtlog.CloseEventLog(hand)

    except ImportError:
        logger.debug("pywin32 not available — Windows Event Log reading disabled")
    except Exception as e:
        logger.debug("Windows Event Log read error: %s", e)

    return rows, new_last


# ---------------------------------------------------------------------------
# Log source registry (Linux)
# ---------------------------------------------------------------------------

LOG_SOURCES = [
    ("/var/log/auth.log", parse_auth_log),
    ("/var/log/ufw.log", parse_ufw_log),
    ("/var/log/nginx/access.log", parse_nginx_access),
    ("/var/log/apache2/access.log", parse_nginx_access),
    ("/var/log/audit/audit.log", parse_audit_log),
    ("/var/log/dhcpd.log", parse_dhcp_log),
    ("/var/log/pihole.log", parse_dns_log),
    ("/var/log/named/default", parse_dns_log),
    ("/var/log/syslog", parse_syslog),
]

# Windows-specific log file paths
WINDOWS_FIREWALL_LOG = r"C:\Windows\System32\LogFiles\Firewall\pfirewall.log"


# ---------------------------------------------------------------------------
# File tailer — tracks file position and reads new lines
# ---------------------------------------------------------------------------

class FileTailer:
    """Tracks a file position and yields new lines on each call."""

    def __init__(self, path: str, parser: Callable):
        self.path = path
        self.parser = parser
        self._position = 0
        self._inode = 0
        self._init_position()

    def _init_position(self):
        try:
            stat = os.stat(self.path)
            self._inode = getattr(stat, 'st_ino', 0)
            self._position = stat.st_size  # start at end (only new lines)
        except OSError:
            pass

    def read_new_lines(self) -> List[Dict[str, Any]]:
        """Read and parse any new lines since last read."""
        results = []
        try:
            stat = os.stat(self.path)
            current_inode = getattr(stat, 'st_ino', 0)
            # Handle log rotation (inode changed or file truncated)
            if current_inode != self._inode or stat.st_size < self._position:
                self._inode = current_inode
                self._position = 0

            if stat.st_size <= self._position:
                return results

            with open(self.path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._position)
                for line in f:
                    parsed = self.parser(line)
                    if parsed:
                        results.append(parsed)
                self._position = f.tell()
        except (OSError, PermissionError):
            pass
        return results


# ---------------------------------------------------------------------------
# Watchdog-based file watcher (thread)
# ---------------------------------------------------------------------------

class LogWatcherThread(threading.Thread):
    """Background thread that uses watchdog + polling to tail multiple log files.

    On Windows, also reads from:
      - Windows Security Event Log (pywin32)
      - Windows Firewall log (pfirewall.log)
      - netstat output (active connections)
    """

    daemon = True

    def __init__(self):
        super().__init__(name="log-watcher")
        self._tailers: List[FileTailer] = []
        self._stop_event = threading.Event()
        self._has_real_sources = False
        # Windows Event Log state
        self._win_evt_last_record = 0
        self._win_evt_available = False
        # Netstat state
        self._netstat_interval = 30  # seconds
        self._last_netstat_time = 0.0
        self._seen_connections: set = set()  # track seen (remote_ip, local_port) to avoid duplicates

    def _discover_sources(self):
        """Find accessible log files and create tailers."""
        if IS_WINDOWS:
            self._discover_windows_sources()
        else:
            self._discover_linux_sources()

        # WATCH_LOG_PATH from env
        watch_path = os.environ.get("WATCH_LOG_PATH", "").strip()
        if watch_path and os.path.exists(watch_path) and os.access(watch_path, os.R_OK):
            if not any(t.path == watch_path for t in self._tailers):
                self._tailers.append(FileTailer(watch_path, parse_auth_log))
                logger.info("log_watcher: monitoring WATCH_LOG_PATH=%s", watch_path)
                self._has_real_sources = True

        # VulnLab access log (cross-platform — lives in data/ dir)
        vulnlab_path = str(DATA_DIR / "vulnlab_access.log")
        if os.path.exists(vulnlab_path) and os.access(vulnlab_path, os.R_OK):
            if not any(t.path == vulnlab_path for t in self._tailers):
                self._tailers.append(FileTailer(vulnlab_path, parse_vulnlab_line))
                logger.info("log_watcher: monitoring VulnLab access log at %s", vulnlab_path)
                self._has_real_sources = True
        else:
            logger.info("log_watcher: VulnLab access log not found at %s", vulnlab_path)

    def _discover_linux_sources(self):
        """Find accessible Linux log files."""
        for path, parser in LOG_SOURCES:
            if os.path.exists(path) and os.access(path, os.R_OK):
                self._tailers.append(FileTailer(path, parser))
                logger.info("log_watcher: monitoring %s", path)
                self._has_real_sources = True

    def _discover_windows_sources(self):
        """Find accessible Windows log sources."""
        # 1. Windows Firewall log
        if os.path.exists(WINDOWS_FIREWALL_LOG) and os.access(WINDOWS_FIREWALL_LOG, os.R_OK):
            self._tailers.append(FileTailer(WINDOWS_FIREWALL_LOG, parse_windows_firewall_log))
            logger.info("log_watcher: monitoring Windows Firewall log at %s", WINDOWS_FIREWALL_LOG)
            self._has_real_sources = True
        else:
            logger.info("log_watcher: Windows Firewall log not accessible at %s", WINDOWS_FIREWALL_LOG)

        # 2. Windows Event Log (pywin32)
        try:
            import win32evtlog
            # Test if we can open the Security log
            hand = win32evtlog.OpenEventLog(None, "Security")
            total = win32evtlog.GetNumberOfEventLogRecords(hand)
            win32evtlog.CloseEventLog(hand)
            self._win_evt_available = True
            # Start from the current end so we only get new events
            self._win_evt_last_record = total
            self._has_real_sources = True
            logger.info("log_watcher: Windows Security Event Log available (%d existing records)", total)
        except ImportError:
            logger.info("log_watcher: pywin32 not installed — Windows Event Log reading disabled. "
                        "Install with: pip install pywin32")
        except Exception as e:
            logger.info("log_watcher: Windows Event Log not accessible (run as admin for Security log): %s", e)

        # 3. netstat is always available on Windows
        self._has_real_sources = True
        logger.info("log_watcher: netstat polling enabled (every %ds)", self._netstat_interval)

    def run(self):
        self._discover_sources()

        use_watchdog = False
        observer = None

        if self._tailers:
            # Try watchdog for efficient event-driven monitoring
            try:
                from watchdog.observers import Observer
                from watchdog.events import FileSystemEventHandler

                class _Handler(FileSystemEventHandler):
                    def __init__(self, watcher_ref):
                        self.watcher = watcher_ref

                    def on_modified(self, event):
                        if event.is_directory:
                            return
                        self.watcher._poll_tailers()

                observer = Observer()
                # Watch each unique directory containing our log files
                watched_dirs = set()
                for tailer in self._tailers:
                    d = os.path.dirname(tailer.path)
                    if d not in watched_dirs:
                        observer.schedule(_Handler(self), d, recursive=False)
                        watched_dirs.add(d)
                observer.start()
                use_watchdog = True
                logger.info("log_watcher: using watchdog for %d directories", len(watched_dirs))
            except ImportError:
                logger.info("log_watcher: watchdog not available, using polling")
            except Exception as e:
                logger.info("log_watcher: watchdog failed (%s), using polling", e)

        if not self._has_real_sources:
            logger.info("log_watcher: no real log sources accessible, running synthetic generator")
            self._run_synthetic()
            return

        logger.info("log_watcher: entering main poll loop (real sources active)")

        # Main loop: poll tailers + Windows sources
        while not self._stop_event.is_set():
            self._poll_tailers()

            if IS_WINDOWS:
                self._poll_windows_event_log()
                self._poll_netstat()

            time.sleep(1.0 if use_watchdog else 0.5)

        if observer:
            observer.stop()
            observer.join()

    def _poll_tailers(self):
        for tailer in self._tailers:
            try:
                rows = tailer.read_new_lines()
                for row in rows:
                    _process_row(row)
            except Exception as e:
                logger.debug("Error reading %s: %s", tailer.path, e)

    def _poll_windows_event_log(self):
        """Read new events from Windows Security Event Log."""
        if not self._win_evt_available:
            return

        try:
            rows, new_last = _read_windows_event_log(self._win_evt_last_record)
            self._win_evt_last_record = new_last
            for row in rows:
                _process_row(row)
        except Exception as e:
            logger.debug("Windows Event Log poll error: %s", e)

    def _poll_netstat(self):
        """Run netstat periodically and emit new connection events."""
        now = time.time()
        if now - self._last_netstat_time < self._netstat_interval:
            return
        self._last_netstat_time = now

        try:
            result = subprocess.run(
                ["netstat", "-an"],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            if result.returncode != 0:
                return

            rows = _parse_netstat_output(result.stdout)

            # Only emit new connections we haven't seen
            current_connections = set()
            for row in rows:
                key = (row["ip_address"], row["endpoint"])
                current_connections.add(key)
                if key not in self._seen_connections:
                    _process_row(row)

            self._seen_connections = current_connections

        except subprocess.TimeoutExpired:
            logger.debug("netstat timed out")
        except Exception as e:
            logger.debug("netstat error: %s", e)

    def _run_synthetic(self):
        """Fallback: generate synthetic logs using chaos_logs logic."""
        import random

        normal_ips = [f"10.0.0.{i}" for i in range(1, 20)]
        attacker_ips = ["192.168.1.55", "45.33.22.11", "203.0.113.8"]
        users = ["alice", "bob", "charlie", "david", "eve", "frank", "grace", "heidi"]
        endpoints = ["/home", "/about", "/products", "/contact", "/login", "/dashboard", "/api/user"]
        attack_endpoints = ["/admin/login", "/wp-admin", "/.env", "/phpmyadmin", "/shell.php"]
        sqli_payloads = [
            "/products?id=1 OR 1=1",
            "/login?user=admin' --",
            "/api/v1/users?id=1; DROP TABLE logs",
            "/search?q=' UNION SELECT username, password FROM users --",
        ]
        statuses_attack = [
            ("Failed_Login", "/admin/login", "admin"),
            ("Failed_Login", "/ssh", "root"),
            ("404_Not_Found", None, "-"),
            ("SQL_Injection", None, "unknown"),
            ("Blocked_Connection", None, "unknown"),
            ("Port_Scan", None, "unknown"),
            ("Sudo_Escalation", "/bin/bash", "eve"),
            ("DNS_Anomaly", "malware.xyz", "unknown"),
        ]

        while not self._stop_event.is_set():
            time.sleep(random.uniform(1.5, 5.0))

            now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            if random.random() < 0.7:
                # Normal traffic
                row = {
                    "timestamp": now,
                    "ip_address": random.choice(normal_ips),
                    "user": random.choice(users),
                    "status": "Success",
                    "endpoint": random.choice(endpoints),
                    "source_log": "synthetic",
                    "raw_line": "",
                }
            else:
                # Attack traffic
                status, ep, user = random.choice(statuses_attack)
                ip = random.choice(attacker_ips)
                if status == "SQL_Injection":
                    ep = random.choice(sqli_payloads)
                elif status == "404_Not_Found" or status == "Port_Scan":
                    ep = random.choice(attack_endpoints)
                elif ep is None:
                    ep = f"port/{random.choice([22, 80, 443, 3306, 8080])}"
                row = {
                    "timestamp": now,
                    "ip_address": ip,
                    "user": user,
                    "status": status,
                    "endpoint": ep,
                    "source_log": "synthetic",
                    "raw_line": "",
                }
            _process_row(row)

    def stop(self):
        self._stop_event.set()


# ---------------------------------------------------------------------------
# Async entry point — called from server.py lifespan
# ---------------------------------------------------------------------------

_watcher_thread: Optional[LogWatcherThread] = None


async def start_watcher() -> None:
    """Start the log watcher thread and keep the async task alive."""
    global _watcher_thread

    _ensure_csv()
    set_event_loop(asyncio.get_running_loop())

    # Enable live monitor so events are always processed and streamed
    set_live_monitor(True)

    _watcher_thread = LogWatcherThread()
    _watcher_thread.start()

    logger.info("log_watcher: background thread started")

    # Keep this coroutine alive so lifespan can cancel it
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        if _watcher_thread:
            _watcher_thread.stop()
            _watcher_thread.join(timeout=5)
# ---------------------------------------------------------------------------
# VulnLab access log — integrated into LogWatcherThread via FileTailer
# ---------------------------------------------------------------------------

_VULNLAB_RE = re.compile(
    r'(?P<ip>\S+) - (?P<user>\S+) \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) [^"]*" '
    r'(?P<status>\d+) \S+'
    r'(?:\s+"[^"]*" "(?P<ua>[^"]*)")?'  # user agent is optional
)

# XSS Detection
XSS_PATTERNS = [
    "<script", "</script>", "javascript:",
    "onerror=", "onload=", "onclick=",
    "alert(", "document.cookie",
    "%3cscript", "%3c/script",
    "&#60;script"
]

# Path Traversal Detection  
PATH_TRAVERSAL_PATTERNS = [
    "../", "..\\", "%2e%2e/", "%2e%2e\\",
    "/etc/passwd", "/etc/shadow",
    "c:\\windows", "c:/windows",
    "/proc/self", "....//", "..%2f"
]

# Command Injection Detection (expand existing)
CMD_INJECTION_PATTERNS = [
    ";", "|", "&&", "||",
    "`", "$(", "${",
    "whoami", "id", "cat /",
    "ls -", "dir ", "ping -",
    "wget ", "curl ", "nc "
]

_vulnlab_entries: List[Dict[str, Any]] = []


def parse_vulnlab_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a vulnlab nginx access log line into the standard pipeline row format.

    Also populates _vulnlab_entries for the /vulnlab-feed endpoint.
    """
    line_s = line.strip()
    if not line_s:
        return None

    m = _VULNLAB_RE.match(line_s)
    if not m:
        return None

    ip = m.group("ip")
    user = m.group("user") if m.group("user") != "-" else "unknown"
    time_str = m.group("time")
    method = m.group("method")
    path = m.group("path")
    http_status = int(m.group("status"))

    # Parse nginx timestamp  "05/Apr/2026:10:30:45 +0530"
    try:
        dt = datetime.strptime(time_str.split()[0], "%d/%b/%Y:%H:%M:%S")
        ts = dt.strftime("%Y-%m-%dT%H:%M:%S")
    except (ValueError, IndexError):
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # XSS check
    path_lower = path.lower()
    if any(p in path_lower for p in XSS_PATTERNS):
        status = "XSS_Attempt"
    elif method == "POST" and any(ep in path_lower for ep in ["/comments", "/search", "/feedback"]):
        status = "XSS_Attempt"
    elif "/comments" in path_lower and method == "GET" and "?" in path_lower:
        status = "XSS_Attempt"
    # Path Traversal check  
    elif any(p in path_lower for p in PATH_TRAVERSAL_PATTERNS):
        status = "Path_Traversal"
    # Expand Command Injection check
    elif "/ping" in path_lower or "/upload" in path_lower and any(c in path_lower for c in CMD_INJECTION_PATTERNS):
        status = "Command_Injection"
    # Also detect command injection in any endpoint
    elif any(c in path for c in [";id", ";whoami", "|id", "&&id", ";cat", "|cat"]):
        status = "Command_Injection"
    # Map HTTP status to security status
    elif _SQLI_RE.search(path):
        status = "SQL_Injection"
    elif http_status in (401, 403):
        status = "Failed_Login"
    elif http_status == 404:
        status = "404_Not_Found"
    elif http_status >= 500:
        status = "500_Server_Error"
    elif http_status >= 400:
        status = "Blocked_Connection"
    else:
        status = "Success"

    # Fire immediate email alert for critical vulnlab attack types
    if status in ("SQL_Injection", "Failed_Login", "Command_Injection", "XSS_Attempt", "Path_Traversal"):
        try:
            from alert_mailer import send_alert_threaded
            
            # Map status to specific threshold names for immediate alerts
            threshold_name_map = {
                "SQL_Injection": "sqli_attempts_per_ip",
                "Failed_Login": "failed_login_per_ip",
                "Command_Injection": "command_injection_detected",
                "XSS_Attempt": "xss_attempt_detected",
                "Path_Traversal": "path_traversal_detected"
            }
            
            _sev = "CRITICAL" if status in ("SQL_Injection", "Command_Injection") else "HIGH"
            _alert = {
                "id": f"vulnlab_{ip}_{int(time.time())}",
                "threshold_name": threshold_name_map.get(status, status),
                "severity": _sev,
                "current_value": 1,
                "threshold_value": 1,
                "ip": ip,  # Use 'ip' to match user's specific request structure if mailer relies on it (though mailer uses ip_address, I include both)
                "ip_address": ip,
                "timestamp": ts,
                "description": f"{status} injection attempt from {ip}: {path}" if status in ("XSS_Attempt", "Command_Injection", "Path_Traversal") else f"{status} detected from {ip} on {method} {path}",
                "auto_block": False,
                "auto_blocked": False,
            }
            send_alert_threaded(_alert)
            logger.info("[%s EMAIL] Fired immediate alert", status)
        except Exception as e:
            logger.warning("Failed to send vulnlab alert email: %s", e)

    # Populate _vulnlab_entries for the /vulnlab-feed endpoint
    entry = {
        "ip": ip,
        "timestamp": time_str,
        "method": method,
        "path": path,
        "status": http_status,
        "user_agent": m.group("ua"),
        "raw": line_s,
    }
    _vulnlab_entries.append(entry)
    if len(_vulnlab_entries) > 100:
        _vulnlab_entries.pop(0)

    logger.info("[VULNLAB] Classified %s %s as %s from %s", method, path, status, ip)
    logger.info("[VULNLAB] Calling threshold evaluate...")

    # Return standard pipeline format for _process_row()
    return {
        "timestamp": ts,
        "ip_address": ip,
        "user": user,
        "status": status,
        "endpoint": f"{method} {path}"[:100],
        "source_log": "vulnlab",
        "raw_line": line_s[:200],
    }
