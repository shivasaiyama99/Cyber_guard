"""
Alert Mailer — sends HTML email alerts via Gmail SMTP when threshold-based
alerts fire. Supports cooldown tracking per-IP to prevent spam.
"""

import json
import logging
import os
import smtplib
import ssl
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

if os.environ.get("IS_VERCEL") == "true":
    DATA_DIR = Path("/tmp/data")
else:
    DATA_DIR = Path(__file__).parent / "data"
EMAIL_AUDIT_FILE = DATA_DIR / "email_audit.json"

_executor = ThreadPoolExecutor(max_workers=2)

# Severity ordering for comparison
_SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _build_html(alert: dict) -> str:
    sev = alert.get("severity", "MEDIUM")
    color = "#f85149" if sev == "CRITICAL" else "#e3b341" if sev == "HIGH" else "#58a6ff"
    auto_status = "BLOCKED" if alert.get("auto_blocked") else "MONITORING"
    return f"""\
<body style="font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 24px;">
  <div style="border: 1px solid #30363d; border-radius: 8px; padding: 20px; max-width: 600px; margin: auto;">
    <h2 style="color: {color};">&#9888;&#65039; Security Alert: {sev}</h2>
    <table style="width: 100%; border-collapse: collapse;">
      <tr><td style="padding: 6px 8px; color: #8b949e;">Threshold:</td><td style="padding: 6px 8px;">{alert.get("threshold_name", "")}</td></tr>
      <tr><td style="padding: 6px 8px; color: #8b949e;">Value:</td><td style="padding: 6px 8px;">{alert.get("current_value", "")} (limit: {alert.get("threshold_value", "")})</td></tr>
      <tr><td style="padding: 6px 8px; color: #8b949e;">Source IP:</td><td style="padding: 6px 8px;">{alert.get("ip_address", "")}</td></tr>
      <tr><td style="padding: 6px 8px; color: #8b949e;">Time:</td><td style="padding: 6px 8px;">{alert.get("timestamp", "")}</td></tr>
      <tr><td style="padding: 6px 8px; color: #8b949e;">Description:</td><td style="padding: 6px 8px;">{alert.get("description", "")}</td></tr>
    </table>
    <p style="color: #8b949e; margin-top: 16px;">Auto-response: {auto_status}</p>
    <a href="http://localhost:5173/monitor" style="color: #58a6ff; text-decoration: none;">View Dashboard &rarr;</a>
  </div>
</body>"""


class AlertMailer:
    def __init__(self):
        self.enabled = os.environ.get("SMTP_ENABLED", "false").strip().lower() == "true"
        self.host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ.get("SMTP_USER", "")
        self.password = os.environ.get("SMTP_PASSWORD", "")
        self.recipients = [
            e.strip() for e in os.environ.get("ALERT_EMAIL_TO", "").split(",") if e.strip()
        ]
        self.min_severity = os.environ.get("ALERT_MIN_SEVERITY", "HIGH").upper()
        self.cooldown_minutes = int(os.environ.get("ALERT_COOLDOWN_MINUTES", "5"))
        self._cooldown_tracker: Dict[str, datetime] = {}
        self._last_sent: Optional[str] = None
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def configured(self) -> bool:
        return bool(self.user and self.password and self.recipients)

    def _check_cooldown(self, ip: str) -> bool:
        """Return True if IP is NOT in cooldown (OK to send)."""
        last = self._cooldown_tracker.get(ip)
        if last is None:
            return True
        return datetime.utcnow() - last > timedelta(minutes=self.cooldown_minutes)

    def _severity_ok(self, severity: str) -> bool:
        return _SEVERITY_ORDER.get(severity, 0) >= _SEVERITY_ORDER.get(self.min_severity, 2)

    def _log_email(self, alert: dict, success: bool, error: str = ""):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "alert_id": alert.get("id", ""),
            "ip_address": alert.get("ip_address", ""),
            "severity": alert.get("severity", ""),
            "success": success,
            "error": error,
        }
        try:
            existing = []
            if EMAIL_AUDIT_FILE.exists():
                existing = json.loads(EMAIL_AUDIT_FILE.read_text())
            existing.append(entry)
            # Keep last 1000 entries
            EMAIL_AUDIT_FILE.write_text(json.dumps(existing[-1000:], indent=2))
        except Exception:
            pass

    def _send_sync(self, subject: str, html: str, recipients: list[str] | None = None) -> tuple:
        """Blocking SMTP send. Returns (success, error_msg)."""
        target = recipients or self.recipients
        if not target:
            return (False, "No recipients")
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.user
            msg["To"] = ", ".join(target)
            msg.attach(MIMEText(html, "html"))

            context = ssl.create_default_context()
            if self.port == 465:
                with smtplib.SMTP_SSL(self.host, self.port, context=context, timeout=15) as server:
                    server.login(self.user, self.password)
                    server.sendmail(self.user, target, msg.as_string())
            else:
                with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(self.user, self.password)
                    server.sendmail(self.user, target, msg.as_string())
            return (True, "")
        except Exception as e:
            return (False, str(e))

    async def send_alert(self, alert: dict):
        """Non-blocking alert email send. Checks severity and cooldown.

        Dynamically sends to all currently logged-in users' emails.
        Falls back to static ALERT_EMAIL_TO if no users are logged in.
        """
        if not self.enabled:
            return

        # Need SMTP credentials even if we have dynamic recipients
        if not self.user or not self.password:
            return

        sev = alert.get("severity", "MEDIUM")
        if not self._severity_ok(sev):
            return

        # Resolve dynamic recipients from active user sessions
        try:
            from auth import get_active_emails
            dynamic_recipients = get_active_emails()
        except Exception:
            dynamic_recipients = []

        # Fall back to static recipients if nobody is logged in
        recipients = dynamic_recipients if dynamic_recipients else self.recipients
        if not recipients:
            logger.warning("No recipients available for alert email (no active users, no fallback)")
            return

        ip = alert.get("ip_address", "0.0.0.0")
        if not self._check_cooldown(ip):
            logger.debug("Alert email skipped for %s — cooldown active", ip)
            return

        subject = f"[CYBERGUARD] {sev} Alert — {alert.get('threshold_name', '')} from {ip}"
        html = _build_html(alert)

        import asyncio
        loop = asyncio.get_event_loop()
        success, error = await loop.run_in_executor(
            _executor, self._send_sync, subject, html, recipients
        )

        if success:
            self._cooldown_tracker[ip] = datetime.utcnow()
            self._last_sent = datetime.utcnow().isoformat()
            logger.info(
                "Alert email sent to %d recipient(s) for %s (%s): %s",
                len(recipients), ip, sev, recipients,
            )
        else:
            logger.warning("Alert email failed: %s", error)

        self._log_email(alert, success, error)

    async def test_connection(self) -> dict:
        """Send a test email. Returns result dict."""
        if not self.configured:
            return {"success": False, "error": "SMTP not configured — set SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_TO"}

        test_alert = {
            "id": "test",
            "severity": "LOW",
            "threshold_name": "Test Alert",
            "current_value": 0,
            "threshold_value": 0,
            "ip_address": "127.0.0.1",
            "timestamp": datetime.utcnow().isoformat(),
            "description": "This is a test email from Cyberguard.",
            "auto_blocked": False,
        }
        subject = "[CYBERGUARD] Test Alert"
        html = _build_html(test_alert)

        import asyncio
        loop = asyncio.get_event_loop()
        success, error = await loop.run_in_executor(_executor, self._send_sync, subject, html)
        if success:
            self._last_sent = datetime.utcnow().isoformat()
        return {"success": success, "error": error}

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "configured": self.configured,
            "last_sent": self._last_sent,
        }


# Singleton
alert_mailer = AlertMailer()


def send_alert_threaded(alert: dict):
    """Fire-and-forget email send in a background thread.

    Safe to call from ANY thread (including background workers like
    log_watcher and threshold_engine) without deadlocking FastAPI's
    main asyncio event loop.
    """
    import threading

    def _run():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(alert_mailer.send_alert(alert))
        except Exception as e:
            logger.warning("Threaded alert email failed: %s", e)
        finally:
            loop.close()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
