"""
Auto-Response Engine — generates and optionally executes containment actions
based on the structured incident report.
"""

import json
import logging
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

if os.environ.get("IS_VERCEL") == "true":
    DATA_DIR = Path("/tmp/data")
    AUDIT_PATH = DATA_DIR / "response_audit.json"
    BLOCKED_IPS_FILE = DATA_DIR / "blocked_ips.json"
else:
    BACKEND_DIR = Path(__file__).parent
    DATA_DIR = BACKEND_DIR / "data"
    AUDIT_PATH = DATA_DIR / "response_audit.json"
    BLOCKED_IPS_FILE = DATA_DIR / "blocked_ips.json"

def _load_blocked_ips() -> set:
    """Load blocked IPs from file on startup."""
    try:
        if BLOCKED_IPS_FILE.exists():
            data = json.loads(BLOCKED_IPS_FILE.read_text())
            return set(data.get("ips", []))
    except Exception:
        pass
    return set()

def _save_blocked_ips():
    """Persist blocked IPs to file."""
    try:
        BLOCKED_IPS_FILE.write_text(
            json.dumps({"ips": list(_blocked_ips)}, indent=2)
        )
    except Exception as e:
        logger.error("Failed to save blocked IPs: %s", e)

# Track IPs we have already blocked this session to avoid duplicate rules
_blocked_ips: Set[str] = _load_blocked_ips()

# IPs that should never be blocked
_SAFE_IPS = {"0.0.0.0", "127.0.0.1", "::1"}

def _is_safe_ip(ip: str) -> bool:
    """Check if an IP should never be blocked (loopback, LAN, localhost)."""
    if ip in _SAFE_IPS:
        return True
    # Never block local network IPs — only block Tailscale (100.x) or public IPs
    if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
        return True
    return False

def _run_block_command(ip: str) -> tuple:
    """Block an IP using cross-platform firewall commands. Returns (success, error_msg)."""
    system = platform.system().lower()
    
    if system == "windows":
        command = (
            f'netsh advfirewall firewall add rule '
            f'name="CyberGuard_Block_{ip}" '
            f'dir=in action=block remoteip={ip} '
            f'protocol=any'
        )
        cmd_args = command.split()
    else:
        command = f'sudo ufw insert 1 deny from {ip} to any'
        cmd_args = ["sudo", "-S", "ufw", "insert", "1", "deny", "from", ip, "to", "any"]
        
    try:
        # Note: on Linux this assumes passwordless sudo for ufw, or it will fail
        result = subprocess.run(
            cmd_args,
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            logger.warning("FIREWALL BLOCKED %s: %s", ip, result.stdout.strip())
            return (True, "", command)
        else:
            if "already exists" in result.stderr.lower() or "already exists" in result.stdout.lower() or "already exists" in command:
                 logger.info("Firewall rule for %s already exists", ip)
                 return (True, "already exists", command)
                 
            err = result.stderr.strip() or result.stdout.strip()
            logger.error("Firewall block failed for %s: %s", ip, err)
            return (False, err, command)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.error("Firewall command failed for %s: %s", ip, e)
        return (False, str(e), command)

def _broadcast_block_event(ip: str, threshold_name: str, dry_run: bool):
    """Inject a block event into the log pipeline so it appears in the frontend."""
    try:
        from log_watcher import _process_row
        _process_row({
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "ip_address": ip,
            "user": "cyberguard",
            "status": "IP_Blocked" if not dry_run else "IP_Block_DryRun",
            "endpoint": f"auto-response/{threshold_name}",
            "source_log": "auto_responder",
            "raw_line": f"{'BLOCKED' if not dry_run else 'DRY-RUN'}: Firewall deny from {ip} (trigger: {threshold_name})",
        })
    except Exception as e:
        logger.debug("Failed to broadcast block event: %s", e)

def _load_audit() -> List[Dict]:
    """Load the response audit log from disk."""
    if AUDIT_PATH.exists():
        try:
            with open(AUDIT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _save_audit(entries: List[Dict]) -> None:
    """Persist the audit log to disk."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, default=str)


def execute_response(report: Optional[Dict] = None, dry_run: bool = True) -> List[Dict]:
    """
    Read the structured report and execute containment actions.

    Args:
        report: The structured report dict (from /report/structured).
        dry_run: If True (default), only log commands without executing.

    Returns:
        List of action records appended to the audit log.
    """
    if report is None:
        return []

    actions: List[Dict] = []
    severity = (report.get("severity") or "").upper()
    source_ip_raw = report.get("source_ip") or ""
    threshold_name = report.get("threshold_name", "manual")

    # Only respond to CRITICAL or HIGH severity
    if severity not in ("CRITICAL", "HIGH"):
        logger.info("Severity is %s — no auto-response triggered.", severity)
        return actions

    # Parse source IPs (may be comma-separated or space-separated)
    import re
    ips = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", source_ip_raw)

    if not ips:
        logger.info("No source IPs found in report — no auto-response triggered.")
        return actions

    for ip in ips:
        # Skip safe IPs and already-blocked IPs
        if _is_safe_ip(ip):
            logger.info("Skipping safe IP %s", ip)
            continue
        if ip in _blocked_ips and not dry_run:
            logger.info("IP %s already blocked this session", ip)
            continue

        executed = False
        error = ""
        command = f"Firewall block for {ip}"
        
        system = platform.system().lower()
        if system == "windows":
            command = (
                f'netsh advfirewall firewall add rule '
                f'name="CyberGuard_Block_{ip}" '
                f'dir=in action=block remoteip={ip} '
                f'protocol=any'
            )
        else:
            command = f'sudo ufw insert 1 deny from {ip} to any'

        if not dry_run:
            success, error, cmd_used = _run_block_command(ip)
            executed = success
            command = cmd_used
            if success:
                _blocked_ips.add(ip)
                _save_blocked_ips()
        else:
            logger.info("DRY RUN: would execute: %s", command)

        # Broadcast to frontend
        _broadcast_block_event(ip, threshold_name, dry_run)

        action_record = {
            "timestamp": datetime.now().isoformat(),
            "ip": ip,
            "action": command,
            "dry_run": dry_run,
            "executed": executed,
            "error": error,
            "trigger": threshold_name,
        }
        actions.append(action_record)

    # Persist to audit log
    audit = _load_audit()
    audit.extend(actions)
    # Keep last 5000 entries
    if len(audit) > 5000:
        audit = audit[-5000:]
    _save_audit(audit)

    return actions


def get_audit_log() -> List[Dict]:
    """Return the full response audit log."""
    return _load_audit()

def unblock_ip(ip: str) -> dict:
    """Remove an IP from the firewall block list."""
    system = platform.system().lower()
    
    if system == "windows":
        command = (
            f'netsh advfirewall firewall delete rule '
            f'name="CyberGuard_Block_{ip}"'
        )
    else:
        command = f'sudo ufw delete deny from {ip} to any'
    
    DRY_RUN = os.environ.get("AUTO_RESPOND_DRY_RUN", "true").lower() == "true"
    try:
        if not DRY_RUN:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True
            )
            success = result.returncode == 0
        else:
            logger.info("DRY RUN: would execute: %s", command)
            success = True
        
        if success:
            _blocked_ips.discard(ip)
            _save_blocked_ips()
            logger.info("Unblocked IP: %s", ip)
            return {"status": "unblocked", "ip": ip}
        else:
            return {"status": "error", "ip": ip, "message": "Command failed"}
    except Exception as e:
        return {"status": "error", "ip": ip, "message": str(e)}

def get_blocked_ips() -> list:
    """Return list of blocked IPs with metadata from audit log."""
    result = []
    try:
        if AUDIT_PATH.exists():
            audit = json.loads(AUDIT_PATH.read_text())
            # Get unique IPs that are currently blocked
            for entry in reversed(audit):
                ip = entry.get("ip")
                if ip and ip in _blocked_ips:
                    # Check if already added
                    if not any(r["ip"] == ip for r in result):
                        result.append({
                            "ip": ip,
                            "blocked_at": entry.get("timestamp", ""),
                            "trigger": entry.get("trigger", "auto"),
                            "dry_run": entry.get("dry_run", True)
                        })
    except Exception as e:
        logger.error("Error reading blocked IPs: %s", e)
    return result

def block_ip(ip: str) -> dict:
    """Manually block a specific IP address."""
    if _is_safe_ip(ip):
        return {"status": "error", "ip": ip, "message": "Cannot block safe IP"}
    if ip in _blocked_ips:
        return {"status": "error", "ip": ip, "message": "IP is already blocked"}
        
    DRY_RUN = os.environ.get("AUTO_RESPOND_DRY_RUN", "true").lower() == "true"
    
    if not DRY_RUN:
        success, error, cmd_used = _run_block_command(ip)
        executed = success
    else:
        success = True
        error = ""
        system = platform.system().lower()
        if system == "windows":
            cmd_used = f'netsh advfirewall firewall add rule name="CyberGuard_Block_{ip}" dir=in action=block remoteip={ip} protocol=any'
        else:
            cmd_used = f'sudo ufw insert 1 deny from {ip} to any'
        logger.info("DRY RUN: would execute: %s", cmd_used)
        executed = False

    if success:
        _blocked_ips.add(ip)
        _save_blocked_ips()
        
        _broadcast_block_event(ip, "manual", DRY_RUN)
        
        audit = _load_audit()
        audit.append({
            "timestamp": datetime.now().isoformat(),
            "ip": ip,
            "action": cmd_used,
            "dry_run": DRY_RUN,
            "executed": executed,
            "error": error,
            "trigger": "manual",
        })
        _save_audit(audit[-5000:])
        return {"status": "blocked", "ip": ip}
    else:
        return {"status": "error", "ip": ip, "message": error}
