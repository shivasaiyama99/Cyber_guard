"""
Threshold Engine — evaluates each incoming log row against configurable
thresholds using sliding-window counts. Fires Alert objects when breached.
Alerts are persisted to backend/data/alerts.json.
"""

import os
import json
import logging
import socket
import uuid
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

if os.environ.get("IS_VERCEL") == "true":
    DATA_DIR = Path("/tmp/data")
    THRESHOLDS_FILE = DATA_DIR / "thresholds.json"
    ALERTS_FILE = DATA_DIR / "alerts.json"
else:
    DATA_DIR = Path(__file__).parent / "data"
    THRESHOLDS_FILE = DATA_DIR / "thresholds.json"
    ALERTS_FILE = DATA_DIR / "alerts.json"
MAX_ALERTS = 10000

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ThresholdConfig(BaseModel):
    # SSH / Auth
    failed_login_per_ip_per_minute: int = 5
    sudo_escalation_per_hour: int = 3
    new_ssh_key_per_day: int = 1

    # Firewall
    blocked_connections_per_ip_per_minute: int = 10
    unique_ports_scanned_per_ip: int = 5

    # Web
    sqli_attempts_per_ip: int = 1
    http_4xx_per_ip_per_minute: int = 20
    http_5xx_per_minute: int = 10

    # Network
    rogue_device_count: int = 1
    dns_anomaly_per_hour: int = 5

    # General
    same_ip_requests_per_minute: int = 100
    # Short-window burst detection: block IP if it sends too many requests in seconds
    burst_requests_per_ip: int = 35
    burst_window_seconds: int = 10

    # DDoS detection
    # Distributed: many DIFFERENT source IPs all getting blocked (DDoS)
    ddos_unique_sources_per_minute: int = 20
    # Command injection attempts
    command_injection_per_ip: int = 1

    # VulnLab & AppSec additions
    dir_scan_per_ip_per_minute: int = 10
    xss_attempt_per_ip_per_minute: int = 3
    path_traversal_per_ip_per_minute: int = 3

    severity_map: Dict[str, str] = Field(default_factory=lambda: {
        "sqli_attempts_per_ip": "CRITICAL",
        "ddos_unique_sources_per_minute": "CRITICAL",
        "burst_requests_per_ip": "CRITICAL",
        "rogue_device_count": "HIGH",
        "failed_login_per_ip_per_minute": "HIGH",
        "blocked_connections_per_ip_per_minute": "HIGH",
        "unique_ports_scanned_per_ip": "HIGH",
        "command_injection_per_ip": "CRITICAL",
        "command_injection_detected": "CRITICAL",
        "xss_attempt_per_ip": "HIGH",
        "path_traversal_per_ip": "HIGH",
        "sudo_escalation_per_hour": "MEDIUM",
        "http_4xx_per_ip_per_minute": "MEDIUM",
        "http_5xx_per_minute": "MEDIUM",
        "dns_anomaly_per_hour": "MEDIUM",
        "dir_scan_per_ip_per_minute": "MEDIUM",
        "new_ssh_key_per_day": "LOW",
        "same_ip_requests_per_minute": "MEDIUM",
    })


class Alert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    threshold_name: str
    current_value: float
    threshold_value: float
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    ip_address: str = "0.0.0.0"
    description: str = ""
    auto_blocked: bool = False


# ---------------------------------------------------------------------------
# ThresholdEngine
# ---------------------------------------------------------------------------


def _get_own_ips() -> set:
    """Detect this machine's own IP addresses and trusted local network."""
    ips = {"127.0.0.1", "::1", "0.0.0.0"}
    try:
        own_ip = socket.gethostbyname(socket.gethostname())
        ips.add(own_ip)
        logger.info("Auto-detected own IP: %s", own_ip)
        # Exclude router/gateway and first few LAN IPs (UPnP/mDNS noise)
        if own_ip.startswith("192.168."):
            subnet = own_ip.rsplit(".", 1)[0]
            for i in range(1, 10):
                ips.add(f"{subnet}.{i}")
    except Exception:
        pass
    return ips


EXCLUDED_IPS = _get_own_ips()
EXCLUDED_ENDPOINTS = {"/status", "/stream", "/alerts/live", "/logs", "/thresholds"}


class ThresholdEngine:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._config = self._load_config()
        self._alerts: List[dict] = self._load_alerts()
        # Clear false alerts from previous runs
        if self._alerts:
            logger.info("Clearing %d old alerts to remove false positives", len(self._alerts))
            self._alerts = []
            try:
                ALERTS_FILE.write_text("[]")
            except Exception:
                pass

        # Per-IP+threshold cooldown: avoid firing same alert repeatedly
        # Key: "ip:threshold_name" -> last fire time
        self._alert_cooldown: Dict[str, datetime] = {}
        self._cooldown_seconds = 30  # suppress duplicate alerts for 30s

    # ---- Persistence -------------------------------------------------------

    def _load_config(self) -> ThresholdConfig:
        if THRESHOLDS_FILE.exists():
            try:
                raw = json.loads(THRESHOLDS_FILE.read_text())
                return ThresholdConfig(**raw)
            except Exception:
                logger.warning("Corrupt thresholds.json — using defaults")
        cfg = ThresholdConfig()
        self._save_config(cfg)
        return cfg

    def _save_config(self, cfg: ThresholdConfig):
        THRESHOLDS_FILE.write_text(cfg.model_dump_json(indent=2))

    def _load_alerts(self) -> List[dict]:
        if ALERTS_FILE.exists():
            try:
                return json.loads(ALERTS_FILE.read_text())
            except Exception:
                return []
        return []

    def _persist_alert(self, alert: Alert):
        self._alerts.append(alert.model_dump())
        # Rotate: keep only last MAX_ALERTS
        if len(self._alerts) > MAX_ALERTS:
            self._alerts = self._alerts[-MAX_ALERTS:]
        try:
            ALERTS_FILE.write_text(json.dumps(self._alerts, indent=2))
        except Exception as e:
            logger.debug("Alert persistence error: %s", e)

    # ---- Public API --------------------------------------------------------

    def get_thresholds(self) -> ThresholdConfig:
        return self._config

    def update_thresholds(self, new_config: ThresholdConfig):
        self._config = new_config
        self._save_config(new_config)
        logger.info("Thresholds updated and persisted")

    def get_alerts(self, limit: int = 500) -> List[dict]:
        return self._alerts[-limit:]

    def evaluate(self, row: dict, recent_logs: deque) -> Optional[Alert]:
        """Check all thresholds against the new row + recent history."""
        cfg = self._config
        ip = row.get("ip_address", "0.0.0.0")
        status = row.get("status", "")
        now = datetime.utcnow()

        # Skip Windows link-local (APIPA) addresses — these are own-machine
        if ip.startswith("169.254."):
            return None

        # Helper: count matching rows in window
        def count_in_window(minutes: int = 1, **match) -> int:
            cutoff = now - timedelta(minutes=minutes)
            total = 0
            for r in recent_logs:
                try:
                    ts = datetime.fromisoformat(r.get("timestamp", ""))
                except (ValueError, TypeError):
                    continue
                if ts < cutoff:
                    continue
                if all(r.get(k) == v for k, v in match.items()):
                    total += 1
            return total

        def make_alert(name: str, current: float, threshold: float, desc: str) -> Optional[Alert]:
            # Cooldown: suppress duplicate alerts for same IP+threshold
            cooldown_key = f"{ip}:{name}"
            last_fire = self._alert_cooldown.get(cooldown_key)
            if last_fire and (now - last_fire).total_seconds() < self._cooldown_seconds:
                return None
            self._alert_cooldown[cooldown_key] = now

            sev = cfg.severity_map.get(name, "MEDIUM")
            a = Alert(
                threshold_name=name,
                current_value=current,
                threshold_value=threshold,
                severity=sev,
                ip_address=ip,
                description=desc,
            )
            self._persist_alert(a)

            # Send email for HIGH and CRITICAL
            if sev in ("HIGH", "CRITICAL"):
                try:
                    from alert_mailer import send_alert_threaded
                    send_alert_threaded(a.model_dump())
                    logger.info("[EMAIL] Sent %s alert for %s", sev, ip)
                except Exception as e:
                    logger.error("[EMAIL] Failed to send: %s", e)

            return a

        # ---- Failed login per IP per minute --------------------------------
        if status == "Failed_Login":
            cnt = count_in_window(1, ip_address=ip, status="Failed_Login")
            if cnt >= cfg.failed_login_per_ip_per_minute:
                return make_alert(
                    "failed_login_per_ip_per_minute", cnt,
                    cfg.failed_login_per_ip_per_minute,
                    f"{cnt} failed logins from {ip} in last minute"
                )

        # ---- Sudo escalation per hour --------------------------------------
        if status == "Sudo_Escalation":
            # Skip sudo from localhost — Windows SYSTEM generates many
            if ip in EXCLUDED_IPS:
                return None
            cnt = count_in_window(60, ip_address=ip, status="Sudo_Escalation")
            # Use higher minimum for sudo to avoid SYSTEM false positives
            effective_threshold = max(cfg.sudo_escalation_per_hour, 200)
            if cnt >= effective_threshold:
                return make_alert(
                    "sudo_escalation_per_hour", cnt,
                    effective_threshold,
                    f"{cnt} sudo escalations from {ip} in last hour"
                )

        # ---- Blocked connections per IP per minute -------------------------
        if status == "Blocked_Connection":
            # Skip local network IPs — router/gateway UPnP/mDNS is normal
            if ip in EXCLUDED_IPS:
                return None
            cnt = count_in_window(1, ip_address=ip, status="Blocked_Connection")

            # DDoS distributed: many DIFFERENT source IPs blocked
            unique_sources = set()
            cutoff_ddos = now - timedelta(minutes=1)
            for r in recent_logs:
                try:
                    ts_r = datetime.fromisoformat(r.get("timestamp", ""))
                except (ValueError, TypeError):
                    continue
                if ts_r < cutoff_ddos:
                    continue
                if r.get("status") == "Blocked_Connection":
                    src = r.get("ip_address", "")
                    if src and src not in EXCLUDED_IPS:
                        unique_sources.add(src)
            if len(unique_sources) >= cfg.ddos_unique_sources_per_minute:
                return make_alert(
                    "ddos_unique_sources_per_minute", len(unique_sources),
                    cfg.ddos_unique_sources_per_minute,
                    f"Distributed DDoS: {len(unique_sources)} unique source IPs blocked in last minute"
                )

            if cnt >= cfg.blocked_connections_per_ip_per_minute:
                return make_alert(
                    "blocked_connections_per_ip_per_minute", cnt,
                    cfg.blocked_connections_per_ip_per_minute,
                    f"{cnt} blocked connections from {ip} in last minute"
                )

        # ---- Port scanning (unique ports per IP) ---------------------------
        if status == "Port_Scan":
            ports = set()
            cutoff = now - timedelta(minutes=5)
            for r in recent_logs:
                try:
                    ts = datetime.fromisoformat(r.get("timestamp", ""))
                except (ValueError, TypeError):
                    continue
                if ts < cutoff:
                    continue
                if r.get("ip_address") == ip and r.get("status") == "Port_Scan":
                    ports.add(r.get("endpoint"))
            if len(ports) >= cfg.unique_ports_scanned_per_ip:
                return make_alert(
                    "unique_ports_scanned_per_ip", len(ports),
                    cfg.unique_ports_scanned_per_ip,
                    f"{ip} scanned {len(ports)} unique ports in 5 minutes"
                )

        # ---- Command Injection (immediate CRITICAL) ------------------------
        if status == "Command_Injection":
            return make_alert(
                "command_injection_detected", 1, 1,
                f"Command injection attempt detected from {ip}: {endpoint}"
            )

        # ---- XSS ATTEMPT ---------------------------------------------------
        if status == "XSS_Attempt":
            cnt = count_in_window(1, ip_address=ip, status="XSS_Attempt")
            logger.info("[THRESHOLD] status=%s ip=%s — checking...", status, ip)
            logger.info("[THRESHOLD] XSS_Attempt count=%d limit=%d", cnt, cfg.xss_attempt_per_ip_per_minute)
            if cnt >= cfg.xss_attempt_per_ip_per_minute:
                return make_alert(
                    "xss_attempt_per_ip", cnt,
                    cfg.xss_attempt_per_ip_per_minute,
                    f"{cnt} XSS attempts from {ip}"
                )

        # ---- PATH TRAVERSAL ------------------------------------------------
        if status == "Path_Traversal":
            cnt = count_in_window(1, ip_address=ip, status="Path_Traversal")
            logger.info("[THRESHOLD] status=%s ip=%s — checking...", status, ip)
            logger.info("[THRESHOLD] Path_Traversal count=%d limit=%d", cnt, cfg.path_traversal_per_ip_per_minute)
            if cnt >= cfg.path_traversal_per_ip_per_minute:
                return make_alert(
                    "path_traversal_per_ip", cnt,
                    cfg.path_traversal_per_ip_per_minute,
                    f"{cnt} path traversal attempts from {ip}"
                )

        # ---- DIRECTORY SCANNING --------------------------------------------
        if status == "Dir_Scan":
            cnt = count_in_window(1, ip_address=ip, status="Dir_Scan")
            if cnt >= cfg.dir_scan_per_ip_per_minute:
                return make_alert(
                    "dir_scan_per_ip_per_minute", cnt,
                    cfg.dir_scan_per_ip_per_minute,
                    f"{cnt} directory scan attempts from {ip} in last minute"
                )

        # ---- SQL Injection (any = immediate alert) -------------------------
        if status == "SQL_Injection":
            cnt = count_in_window(5, ip_address=ip, status="SQL_Injection")
            if cnt >= cfg.sqli_attempts_per_ip:
                return make_alert(
                    "sqli_attempts_per_ip", cnt,
                    cfg.sqli_attempts_per_ip,
                    f"SQL injection attempt from {ip}"
                )

        # ---- HTTP 4xx per IP per minute ------------------------------------
        if status == "404_Not_Found":
            cnt = count_in_window(1, ip_address=ip, status="404_Not_Found")
            if cnt >= cfg.http_4xx_per_ip_per_minute:
                return make_alert(
                    "http_4xx_per_ip_per_minute", cnt,
                    cfg.http_4xx_per_ip_per_minute,
                    f"{cnt} 4xx errors from {ip} in last minute"
                )

        # ---- HTTP 5xx per minute (global) ----------------------------------
        if status == "500_Server_Error":
            cnt = count_in_window(1, status="500_Server_Error")
            if cnt >= cfg.http_5xx_per_minute:
                return make_alert(
                    "http_5xx_per_minute", cnt,
                    cfg.http_5xx_per_minute,
                    f"{cnt} server errors in last minute"
                )

        # ---- Rogue device --------------------------------------------------
        if status == "Rogue_Device":
            cnt = count_in_window(60, status="Rogue_Device")
            if cnt >= cfg.rogue_device_count:
                return make_alert(
                    "rogue_device_count", cnt,
                    cfg.rogue_device_count,
                    f"Rogue device detected: {ip}"
                )

        # ---- DNS anomaly per hour ------------------------------------------
        if status == "DNS_Anomaly":
            cnt = count_in_window(60, status="DNS_Anomaly")
            if cnt >= cfg.dns_anomaly_per_hour:
                return make_alert(
                    "dns_anomaly_per_hour", cnt,
                    cfg.dns_anomaly_per_hour,
                    f"{cnt} DNS anomalies in last hour"
                )

        # ---- Burst detection: N requests in X seconds (auto-block) ----------
        if ip != "0.0.0.0" and ip not in EXCLUDED_IPS:
            cutoff_burst = now - timedelta(seconds=cfg.burst_window_seconds)
            burst_cnt = 0
            for r in recent_logs:
                try:
                    ts_r = datetime.fromisoformat(r.get("timestamp", ""))
                except (ValueError, TypeError):
                    continue
                if ts_r < cutoff_burst:
                    continue
                if r.get("ip_address") == ip:
                    burst_cnt += 1
            if burst_cnt >= cfg.burst_requests_per_ip:
                return make_alert(
                    "burst_requests_per_ip", burst_cnt,
                    cfg.burst_requests_per_ip,
                    f"BURST: {ip} sent {burst_cnt} requests in {cfg.burst_window_seconds}s — auto-blocking"
                )

        # ---- General rate limit per IP per minute --------------------------
        endpoint = row.get("endpoint", "")

        if ip not in EXCLUDED_IPS and endpoint not in EXCLUDED_ENDPOINTS:
            cnt = count_in_window(1, ip_address=ip)
            if cnt >= cfg.same_ip_requests_per_minute:
                return make_alert(
                    "same_ip_requests_per_minute", cnt,
                    cfg.same_ip_requests_per_minute,
                    f"{ip} sent {cnt} requests in last minute"
                )

        return None
