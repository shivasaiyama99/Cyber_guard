"""
Port Scanner — runs nmap scans asynchronously, compares results against
an allowlist, and stores scan history.
"""

import asyncio
import json
import logging
import os
import platform
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

if os.environ.get("IS_VERCEL") == "true":
    DATA_DIR = Path("/tmp/data")
    ALLOWED_PORTS_FILE = DATA_DIR / "allowed_ports.json"
    SCAN_HISTORY_FILE = DATA_DIR / "port_scan_history.json"
else:
    DATA_DIR = Path(__file__).parent / "data"
    ALLOWED_PORTS_FILE = DATA_DIR / "allowed_ports.json"
    SCAN_HISTORY_FILE = DATA_DIR / "port_scan_history.json"

DEFAULT_ALLOWED_PORTS = [22, 80, 443, 5173, 8000, 9090]
COMMON_PORTS = "21,22,23,25,80,443,3306,3389,5173,6379,8000,8080,27017"
CRITICAL_PORTS = "8000,5173,27017,3389,80,443,22"
MAX_HISTORY = 50


def _find_nmap() -> str | None:
    """Locate the nmap executable, checking common Windows paths first."""
    if platform.system() == "Windows":
        win_paths = [
            r"C:\Program Files (x86)\Nmap\nmap.exe",
            r"C:\Program Files\Nmap\nmap.exe",
        ]
        for p in win_paths:
            if os.path.isfile(p):
                logger.info("Found nmap at %s", p)
                return p

    # Fall back to PATH lookup (works on all platforms)
    found = shutil.which("nmap")
    if found:
        logger.info("Found nmap on PATH: %s", found)
        return found

    return None


class PortScanner:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._allowed = self._load_allowed()
        self._nmap_path = _find_nmap()
        if self._nmap_path:
            logger.info("nmap ready: %s", self._nmap_path)
        else:
            logger.warning("nmap not found — scans will fail until nmap is installed")

    def _load_allowed(self) -> List[int]:
        if ALLOWED_PORTS_FILE.exists():
            try:
                return json.loads(ALLOWED_PORTS_FILE.read_text())
            except Exception:
                pass
        self._save_allowed(DEFAULT_ALLOWED_PORTS)
        return DEFAULT_ALLOWED_PORTS

    def _save_allowed(self, ports: List[int]):
        ALLOWED_PORTS_FILE.write_text(json.dumps(sorted(set(ports)), indent=2))

    def _load_history(self) -> List[dict]:
        if SCAN_HISTORY_FILE.exists():
            try:
                return json.loads(SCAN_HISTORY_FILE.read_text())
            except Exception:
                return []
        return []

    def _save_history(self, history: List[dict]):
        SCAN_HISTORY_FILE.write_text(json.dumps(history[-MAX_HISTORY:], indent=2))

    def update_allowed(self, ports: List[int]):
        self._allowed = sorted(set(ports))
        self._save_allowed(self._allowed)
        logger.info("Allowed ports updated: %s", self._allowed)

    def get_allowed(self) -> List[int]:
        return self._allowed

    def get_history(self, limit: int = 10) -> List[dict]:
        return self._load_history()[-limit:]

    async def _run_nmap(self, target: str, ports: str) -> tuple[list[dict], str, str, int]:
        """Run nmap with -sT (TCP connect scan) and return (open_ports, stdout, stderr, returncode).

        Uses subprocess.run via run_in_executor for Windows compatibility
        (asyncio.create_subprocess_exec fails on Windows with SelectorEventLoop).
        """
        import subprocess as _sp
        import sys

        cmd = [
            self._nmap_path, "-sT", "-p", ports, "--open",
            "--host-timeout", "15s", "--max-retries", "1",
            target, "-oX", "-",
        ]
        print(f"[SCAN DEBUG] nmap_path = {self._nmap_path}")
        print(f"[SCAN DEBUG] calling _run_nmap with target={target} ports={ports}")
        print(f"[SCAN DEBUG] full cmd = {cmd}")
        logger.info("Running: %s", " ".join(cmd))

        loop = asyncio.get_event_loop()

        # On Windows, use CREATE_NO_WINDOW to prevent console pop-up and potential blocking
        extra_kwargs = {}
        if sys.platform == "win32":
            extra_kwargs["creationflags"] = getattr(_sp, "CREATE_NO_WINDOW", 0x08000000)

        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: _sp.run(cmd, capture_output=True, timeout=30, **extra_kwargs),
                ),
                timeout=60,
            )
        except asyncio.TimeoutError:
            print("[SCAN DEBUG] TIMEOUT after 180s")
            raise
        except Exception as e:
            print(f"[SCAN DEBUG] EXCEPTION in run_in_executor: {type(e).__name__}: {e}")
            raise

        xml_out = result.stdout.decode(errors="replace")
        stderr_out = result.stderr.decode(errors="replace")
        rc = result.returncode

        print(f"[SCAN DEBUG] _run_nmap returned rc={rc} stdout_len={len(xml_out)}")
        print(f"[SCAN DEBUG] xml_out preview: {xml_out[:300]}")
        if stderr_out.strip():
            print(f"[SCAN DEBUG] stderr_out: {stderr_out[:200]}")

        logger.info("nmap XML output: %s", xml_out[:500])
        if stderr_out.strip():
            logger.info("nmap stderr: %s", stderr_out[:200])

        open_ports = []
        if rc == 0:
            open_ports = self._parse_xml(xml_out)

        print(f"[SCAN DEBUG] open_ports found: {len(open_ports)}")
        logger.info("Open ports found: %d", len(open_ports))
        return open_ports, xml_out, stderr_out, rc

    async def scan(self, target: str = "127.0.0.1", ports: str = COMMON_PORTS) -> dict:
        """Run a real nmap scan. Returns an error result if nmap is not found."""
        # Re-check for nmap in case it was installed after startup
        if not self._nmap_path:
            self._nmap_path = _find_nmap()

        if not self._nmap_path:
            result = {
                "target": target,
                "timestamp": datetime.utcnow().isoformat(),
                "scan_time": "0.0s",
                "open_ports": [],
                "unexpected_ports": [],
                "allowed_ports": self._allowed,
                "mock_data": False,
                "error": "nmap not found. Install from https://nmap.org/download.html",
            }
            self._store_result(result)
            return result

        start = datetime.utcnow()

        try:
            open_ports, xml_out, stderr_out, rc = await self._run_nmap(target, ports)

            if rc != 0:
                logger.warning("nmap error (rc=%d): %s", rc, stderr_out[:300])
                result = {
                    "target": target,
                    "timestamp": start.isoformat(),
                    "scan_time": "0.0s",
                    "open_ports": [],
                    "unexpected_ports": [],
                    "allowed_ports": self._allowed,
                    "mock_data": False,
                    "error": f"nmap exited with code {rc}: {stderr_out[:300]}",
                }
                self._store_result(result)
                return result

            # Fallback: if 0 ports found, retry with critical ports only
            if len(open_ports) == 0:
                logger.info("No open ports found with full list, retrying with critical ports: %s", CRITICAL_PORTS)
                open_ports, xml_out, stderr_out, rc = await self._run_nmap(target, CRITICAL_PORTS)
                if rc != 0:
                    logger.warning("nmap retry error (rc=%d): %s", rc, stderr_out[:300])

        except asyncio.TimeoutError:
            result = {
                "target": target,
                "timestamp": start.isoformat(),
                "scan_time": "180.0s",
                "open_ports": [],
                "unexpected_ports": [],
                "allowed_ports": self._allowed,
                "mock_data": False,
                "error": "nmap timed out after 180s",
            }
            self._store_result(result)
            return result
        except Exception as e:
            print(f"[SCAN DEBUG] scan() caught exception: {type(e).__name__}: {e}")
            result = {
                "target": target,
                "timestamp": start.isoformat(),
                "scan_time": "0.0s",
                "open_ports": [],
                "unexpected_ports": [],
                "allowed_ports": self._allowed,
                "mock_data": False,
                "error": str(e),
            }
            self._store_result(result)
            return result

        unexpected = [p for p in open_ports if p["port"] not in self._allowed]
        elapsed = (datetime.utcnow() - start).total_seconds()

        result = {
            "target": target,
            "timestamp": start.isoformat(),
            "scan_time": f"{elapsed:.1f}s",
            "open_ports": open_ports,
            "unexpected_ports": unexpected,
            "allowed_ports": self._allowed,
            "mock_data": False,
        }
        self._store_result(result)

        # Verify persistence
        try:
            saved = self._load_history()
            if saved:
                logger.info("Verified scan saved to history. Last entry ports: %s",
                            [p["port"] for p in saved[-1].get("open_ports", [])])
            else:
                logger.warning("Scan history file is empty after save!")
        except Exception as e:
            logger.warning("Could not verify scan history: %s", e)

        return result

    def _parse_xml(self, xml_str: str) -> List[dict]:
        """Parse nmap XML output into a list of port dicts."""
        ports = []
        try:
            root = ET.fromstring(xml_str)
            hosts = root.findall(".//host")
            logger.info("XML parse: found %d host element(s)", len(hosts))
            for host in hosts:
                port_elements = host.findall(".//port")
                logger.info("XML parse: host has %d port element(s)", len(port_elements))
                for port_el in port_elements:
                    state_el = port_el.find("state")
                    service_el = port_el.find("service")
                    state_val = state_el.get("state") if state_el is not None else "unknown"
                    logger.info("XML parse: port %s state=%s", port_el.get("portid"), state_val)
                    if state_el is not None and state_el.get("state") == "open":
                        ports.append({
                            "port": int(port_el.get("portid", 0)),
                            "protocol": port_el.get("protocol", "tcp"),
                            "state": "open",
                            "service": service_el.get("name", "unknown") if service_el is not None else "unknown",
                            "version": service_el.get("version", "") if service_el is not None else "",
                        })
        except ET.ParseError as e:
            logger.warning("nmap XML parse error: %s", e)
        return ports

    def _store_result(self, result: dict):
        history = self._load_history()
        history.append(result)
        self._save_history(history)


# Singleton
port_scanner = PortScanner()
