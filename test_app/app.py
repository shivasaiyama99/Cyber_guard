"""
VulnLab — Deliberately Vulnerable Web Application for Security Testing.

⚠️  THIS APPLICATION IS INTENTIONALLY INSECURE.
    DO NOT DEPLOY TO ANY PUBLIC NETWORK.
    For local security testing only.
"""

import os
import signal
import sqlite3
import subprocess
import threading
from datetime import datetime, timezone

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    send_from_directory,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ─── Access log for Cyberguard monitoring ───────────────────────────────────
# Written in nginx combined log format so backend/log_watcher.py can parse it.
# Path can be overridden by VULNLAB_LOG_PATH env var.
_VULNLAB_LOG = os.environ.get(
    "VULNLAB_LOG_PATH",
    os.path.join(BASE_DIR, "..", "backend", "data", "vulnlab_access.log"),
)

app = Flask(__name__)
app.secret_key = "super-secret-key-123"  # Intentionally weak


# ─── Access log middleware ───────────────────────────────────────────────────

@app.after_request
def _write_access_log(response):
    """Write every request to a nginx-format access log for Cyberguard monitoring.

    Format: IP - user [dd/Mon/YYYY:HH:MM:SS +0000] "METHOD URI HTTP/1.1" status -
    This is parsed by backend/log_watcher.py parse_nginx_access().
    """
    try:
        print(f"[LOGGING] Writing log for {request.remote_addr}")
        ts = datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")
        user = session.get("username", "-") or "-"
        # Include query string so SQLi payloads are visible in the log
        uri = request.full_path.rstrip("?") if not request.query_string else request.full_path
        ip = (request.headers.get("X-Forwarded-For", "") or request.remote_addr or "127.0.0.1").split(",")[0].strip()
        
        line = '{ip} - {user} [{ts}] "{method} {uri} HTTP/1.1" {status} - "-" "{ua}"\n'.format(
            ip=ip, user=user, ts=ts, method=request.method, uri=uri, 
            status=response.status_code, ua=request.headers.get("User-Agent", "-")
        )
        
        os.makedirs(os.path.dirname(os.path.abspath(_VULNLAB_LOG)), exist_ok=True)
        with open(_VULNLAB_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # Never break responses due to logging errors
    return response


# ─── Helpers ────────────────────────────────────────────────────────────────

def get_db():
    """Return a raw sqlite3 connection (no ORM, no safety)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Pages ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── 1. LOGIN — Brute-force target (no rate limiting, no lockout) ────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        # VULNERABLE: string formatting in SQL query
        db = get_db()
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        try:
            user = db.execute(query).fetchone()
        except Exception as e:
            error = str(e)
            user = None
        db.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("profile", user_id=user["id"]))
        elif not error:
            error = "Invalid username or password"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ── 2. PRODUCTS — SQL Injection target ──────────────────────────────────────

@app.route("/products")
def products():
    db = get_db()
    search = request.args.get("search", "")
    category = request.args.get("category", "")
    product_id = request.args.get("id", "")

    if product_id:
        # VULNERABLE: Direct string interpolation in SQL
        query = f"SELECT * FROM products WHERE id = {product_id}"
    elif search:
        # VULNERABLE: Direct string interpolation in SQL
        query = f"SELECT * FROM products WHERE name LIKE '%{search}%' OR description LIKE '%{search}%'"
    elif category:
        # VULNERABLE: Direct string interpolation in SQL
        query = f"SELECT * FROM products WHERE category = '{category}'"
    else:
        query = "SELECT * FROM products"

    try:
        rows = db.execute(query).fetchall()
        error = None
    except Exception as e:
        rows = []
        error = str(e)  # VULNERABLE: exposes internal DB errors
    db.close()

    return render_template("products.html", products=rows, search=search, category=category, error=error)


# ── 3. USER PROFILE — IDOR target (no authorization check) ─────────────────

@app.route("/profile/<int:user_id>")
def profile(user_id):
    db = get_db()
    # VULNERABLE: No authorization check — any user can view any profile
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    if not user:
        return render_template("profile.html", user=None, error="User not found")
    return render_template("profile.html", user=user, error=None)


# ── 4. PING — Command Injection target ─────────────────────────────────────

@app.route("/ping", methods=["GET", "POST"])
def ping():
    output = None
    host = ""
    if request.method == "POST":
        host = request.form.get("host", "")
        # VULNERABLE: Direct command injection via shell=True
        try:
            result = subprocess.run(
                f"ping -c 2 {host}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            output = "Command timed out (10s limit)"
        except Exception as e:
            output = f"Error: {e}"

    return render_template("ping.html", output=output, host=host)


# ── 5. FILE UPLOAD — Unrestricted upload target ────────────────────────────

@app.route("/upload", methods=["GET", "POST"])
def upload():
    message = None
    msg_type = None
    if request.method == "POST":
        f = request.files.get("file")
        if f and f.filename:
            # VULNERABLE: No file type validation, no size limit, original filename used
            filepath = os.path.join(UPLOAD_DIR, f.filename)
            f.save(filepath)
            message = f"File uploaded: /uploads/{f.filename} ({os.path.getsize(filepath)} bytes)"
            msg_type = "success"
        else:
            message = "No file selected"
            msg_type = "error"

    # List uploaded files
    files = []
    for fname in os.listdir(UPLOAD_DIR):
        fpath = os.path.join(UPLOAD_DIR, fname)
        if os.path.isfile(fpath):
            files.append({"name": fname, "size": os.path.getsize(fpath)})

    return render_template("upload.html", message=message, msg_type=msg_type, files=files)


# Serve uploaded files directly (VULNERABLE: no access control)
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ── 6. COMMENTS — Stored XSS target ────────────────────────────────────────

@app.route("/comments", methods=["GET", "POST"])
def comments():
    db = get_db()
    message = None

    if request.method == "POST":
        author = request.form.get("author", "Anonymous")
        comment = request.form.get("comment", "")
        if comment.strip():
            # VULNERABLE: Stores raw HTML/JS — will be rendered unescaped
            db.execute("INSERT INTO comments (author, message) VALUES (?, ?)", (author, comment))
            db.commit()
            message = "Comment posted!"

    rows = db.execute("SELECT * FROM comments ORDER BY created_at DESC").fetchall()
    db.close()
    return render_template("comments.html", comments=rows, message=message)


# ── 7. ADMIN — Hidden directory target ─────────────────────────────────────

@app.route("/admin")
def admin():
    db = get_db()
    users = db.execute("SELECT id, username, email, role FROM users").fetchall()
    products = db.execute("SELECT id, name, price, stock FROM products").fetchall()
    db.close()
    return render_template("admin.html", users=users, products=products)


# ── 8. API ENDPOINTS — Automated tool targets ──────────────────────────────

@app.route("/api/users")
def api_users():
    """VULNERABLE: SQL injection via search parameter."""
    db = get_db()
    search = request.args.get("search", "")
    if search:
        query = f"SELECT id, username, email, role FROM users WHERE username LIKE '%{search}%'"
    else:
        query = "SELECT id, username, email, role FROM users"
    try:
        rows = db.execute(query).fetchall()
        result = [dict(row) for row in rows]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/products")
def api_products():
    """VULNERABLE: SQL injection via id or search parameter."""
    db = get_db()
    pid = request.args.get("id", "")
    search = request.args.get("search", "")
    if pid:
        query = f"SELECT * FROM products WHERE id = {pid}"
    elif search:
        query = f"SELECT * FROM products WHERE name LIKE '%{search}%'"
    else:
        query = "SELECT * FROM products"
    try:
        rows = db.execute(query).fetchall()
        result = [dict(row) for row in rows]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/login", methods=["POST"])
def api_login():
    """VULNERABLE: No rate limiting, SQL injection possible."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", request.form.get("username", ""))
    password = data.get("password", request.form.get("password", ""))

    db = get_db()
    query = f"SELECT id, username, role FROM users WHERE username = '{username}' AND password = '{password}'"
    try:
        user = db.execute(query).fetchone()
        if user:
            return jsonify({"success": True, "user": dict(user)})
        return jsonify({"success": False, "error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


# ── Hidden static files (directory brute-force targets) ─────────────────────

@app.route("/backup/<path:filename>")
def backup_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, "backup"), filename)


@app.route("/secret/<path:filename>")
def secret_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, "secret"), filename)


@app.route("/config")
def config():
    return jsonify({
        "database": DB_PATH,
        "secret_key": app.secret_key,
        "debug": True,
        "upload_dir": UPLOAD_DIR,
    })


@app.route("/robots.txt")
def robots():
    return (
        "User-agent: *\n"
        "Disallow: /admin\n"
        "Disallow: /backup\n"
        "Disallow: /secret\n"
        "Disallow: /config\n"
    ), 200, {"Content-Type": "text/plain"}


@app.route("/.env")
def env_file():
    return send_from_directory(BASE_DIR, ".env")


# ── 9. SYSTEM LOGS — Real system log viewer (VULNERABLE: info disclosure) ──

@app.route("/logs")
def system_logs():
    """VULNERABLE: Exposes real system logs — information disclosure."""
    log_file = request.args.get("file", "/var/log/auth.log")
    lines = int(request.args.get("lines", "50"))
    try:
        result = subprocess.run(
            f"tail -n {lines} {log_file}",
            shell=True,  # VULNERABLE: command injection via log_file param
            capture_output=True,
            text=True,
            timeout=5,
        )
        content = result.stdout or result.stderr
    except Exception as e:
        content = f"Error: {e}"
    return render_template("logs.html", content=content, log_file=log_file, lines=lines)


@app.route("/api/logs")
def api_system_logs():
    """VULNERABLE: Exposes real system logs via API."""
    log_file = request.args.get("file", "/var/log/syslog")
    lines = int(request.args.get("lines", "100"))
    try:
        result = subprocess.run(
            ["tail", "-n", str(lines), log_file],
            capture_output=True,
            text=True,
            timeout=5,
        )
        log_lines = result.stdout.splitlines()
        return jsonify({"file": log_file, "lines": log_lines, "count": len(log_lines)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/system-info")
def api_system_info():
    """VULNERABLE: Exposes system information."""
    import platform as plat
    info = {
        "hostname": subprocess.getoutput("hostname"),
        "os": plat.platform(),
        "kernel": subprocess.getoutput("uname -r"),
        "uptime": subprocess.getoutput("uptime"),
        "whoami": subprocess.getoutput("whoami"),
        "groups": subprocess.getoutput("groups"),
        "open_ports": subprocess.getoutput("ss -tlnp 2>/dev/null | head -20"),
        "processes": subprocess.getoutput("ps aux --sort=-%mem | head -15"),
        "network": subprocess.getoutput("ip addr show 2>/dev/null | head -30"),
    }
    return jsonify(info)


@app.route("/api/active-connections")
def api_active_connections():
    """VULNERABLE: Exposes active network connections."""
    try:
        result = subprocess.run(
            ["ss", "-tnp"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return jsonify({"connections": result.stdout.splitlines()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 10. DDoS SIMULATOR — trigger DDoS attack from the browser ──────────

# Track running attack processes so they can be stopped
_ddos_proc: dict = {"process": None, "thread": None, "status": "idle", "target": "", "port": 0, "attack": ""}


def _run_ddos(target: str, port: int, attack: str, duration: int, threads: int):
    """Run ddos_simulate.py in a subprocess."""
    script = os.path.join(BASE_DIR, "ddos_simulate.py")
    cmd = [
        "python3", script,
        "--target", target,
        "--port", str(port),
        "--attack", attack,
        "--duration", str(duration),
        "--threads", str(threads),
    ]
    _ddos_proc["status"] = "running"
    _ddos_proc["target"] = target
    _ddos_proc["port"] = port
    _ddos_proc["attack"] = attack
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        _ddos_proc["process"] = proc
        proc.wait()
    except Exception:
        pass
    finally:
        _ddos_proc["status"] = "idle"
        _ddos_proc["process"] = None


@app.route("/ddos", methods=["GET", "POST"])
def ddos():
    output = None
    error = None

    if request.method == "POST":
        action = request.form.get("action", "start")

        if action == "stop":
            proc = _ddos_proc.get("process")
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                _ddos_proc["status"] = "idle"
                _ddos_proc["process"] = None
                output = "Attack stopped."
            else:
                error = "No attack currently running."
        else:
            # Start attack
            target = request.form.get("target", "").strip()
            port = request.form.get("port", "").strip()
            attack_type = request.form.get("attack", "http")
            duration = request.form.get("duration", "30").strip()
            threads = request.form.get("threads", "20").strip()

            if not target:
                error = "Target IP/hostname is required"
            elif not port or not port.isdigit():
                error = "A valid port number is required"
            elif _ddos_proc["status"] == "running":
                error = "An attack is already running. Stop it first."
            else:
                port_int = int(port)
                duration_int = min(int(duration), 300)  # cap at 5 min
                threads_int = min(int(threads), 100)   # cap at 100

                t = threading.Thread(
                    target=_run_ddos,
                    args=(target, port_int, attack_type, duration_int, threads_int),
                    daemon=True,
                )
                t.start()
                _ddos_proc["thread"] = t
                output = f"Attack started: {attack_type} flood on {target}:{port_int} for {duration_int}s with {threads_int} threads"

    return render_template(
        "ddos.html",
        output=output,
        error=error,
        status=_ddos_proc["status"],
        current_target=_ddos_proc.get("target", ""),
        current_port=_ddos_proc.get("port", 0),
        current_attack=_ddos_proc.get("attack", ""),
    )


@app.route("/api/ddos", methods=["POST"])
def api_ddos():
    """API endpoint to trigger DDoS simulation (for remote use)."""
    data = request.get_json(silent=True) or {}
    target = data.get("target", "").strip()
    port = data.get("port", 0)
    attack = data.get("attack", "http")
    duration = min(data.get("duration", 30), 300)
    threads = min(data.get("threads", 20), 100)

    if not target or not port:
        return jsonify({"error": "target and port are required"}), 400

    if _ddos_proc["status"] == "running":
        return jsonify({"error": "attack already running", "status": _ddos_proc["status"]}), 409

    t = threading.Thread(
        target=_run_ddos,
        args=(target, int(port), attack, duration, threads),
        daemon=True,
    )
    t.start()
    return jsonify({
        "status": "started",
        "target": target,
        "port": port,
        "attack": attack,
        "duration": duration,
        "threads": threads,
    })


@app.route("/api/ddos/stop", methods=["POST"])
def api_ddos_stop():
    """API endpoint to stop a running DDoS simulation."""
    proc = _ddos_proc.get("process")
    if proc and proc.poll() is None:
        proc.terminate()
        _ddos_proc["status"] = "idle"
        _ddos_proc["process"] = None
        return jsonify({"status": "stopped"})
    return jsonify({"status": "idle", "message": "no attack running"})


@app.route("/api/ddos/status")
def api_ddos_status():
    """API endpoint to check DDoS simulation status."""
    return jsonify({
        "status": _ddos_proc["status"],
        "target": _ddos_proc.get("target", ""),
        "port": _ddos_proc.get("port", 0),
        "attack": _ddos_proc.get("attack", ""),
    })


# ── Health / status ─────────────────────────────────────────────────────────

@app.route("/status")
def status():
    return jsonify({"status": "running", "app": "VulnLab", "version": "1.0.0"})


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    # Auto-initialize DB if missing
    if not os.path.exists(DB_PATH):
        from init_db import init
        init()

    app.run(host="0.0.0.0", port=9090, debug=True)


if __name__ == "__main__":
    main()
