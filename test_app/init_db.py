"""
Initialize the SQLite database with sample data for vulnerability testing.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


def init():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ── Users table (brute-force & SQLi target) ──
    c.execute("DROP TABLE IF EXISTS users")
    c.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'user',
            credit_card TEXT,
            ssn TEXT
        )
    """)
    users = [
        ("admin",   "admin123",     "admin@vulnlab.local",   "admin",  "4111-1111-1111-1111", "123-45-6789"),
        ("john",    "password",     "john@vulnlab.local",    "user",   "4222-2222-2222-2222", "234-56-7890"),
        ("jane",    "letmein",      "jane@vulnlab.local",    "user",   "4333-3333-3333-3333", "345-67-8901"),
        ("bob",     "qwerty",       "bob@vulnlab.local",     "user",   "4444-4444-4444-4444", "456-78-9012"),
        ("alice",   "trustno1",     "alice@vulnlab.local",   "editor", "4555-5555-5555-5555", "567-89-0123"),
        ("charlie", "dragon",       "charlie@vulnlab.local", "user",   "4666-6666-6666-6666", "678-90-1234"),
        ("dave",    "monkey",       "dave@vulnlab.local",    "user",   "4777-7777-7777-7777", "789-01-2345"),
        ("eve",     "master",       "eve@vulnlab.local",     "user",   "4888-8888-8888-8888", "890-12-3456"),
        ("frank",   "abc123",       "frank@vulnlab.local",   "user",   "4999-9999-9999-9999", "901-23-4567"),
        ("grace",   "iloveyou",     "grace@vulnlab.local",   "user",   "4000-0000-0000-0000", "012-34-5678"),
    ]
    c.executemany(
        "INSERT INTO users (username, password, email, role, credit_card, ssn) VALUES (?, ?, ?, ?, ?, ?)",
        users,
    )

    # ── Products table (SQLi target) ──
    c.execute("DROP TABLE IF EXISTS products")
    c.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL,
            category TEXT,
            stock INTEGER DEFAULT 0
        )
    """)
    products = [
        ("Quantum Firewall X1",        "Next-gen AI-powered network firewall",                   2999.99, "Hardware",  15),
        ("CryptoVault Pro",            "Military-grade encrypted storage drive 2TB",              899.99,  "Hardware",  42),
        ("NetSentry IDS",              "Intrusion detection system with ML anomaly detection",    4500.00, "Software",  100),
        ("ZeroDay Shield",             "Real-time zero-day threat prevention suite",              1299.00, "Software",  200),
        ("BioAuth Scanner",            "Multi-factor biometric authentication device",            599.99,  "Hardware",  30),
        ("DarkNet Monitor",            "Dark web credential leak monitoring service",             79.99,   "Service",   999),
        ("Phantom VPN Gateway",        "Enterprise VPN appliance with quantum-safe encryption",   3499.00, "Hardware",  8),
        ("ThreatHunter Elite",         "Automated penetration testing platform",                  6999.00, "Software",  50),
        ("SecureComm Radio",           "Encrypted tactical communication device",                 1899.00, "Hardware",  20),
        ("Incident Response Toolkit",  "Complete IR toolkit with forensic analysis tools",        2499.00, "Software",  75),
        ("WiFi Pineapple Mark VIII",   "Wireless auditing platform for security professionals",   449.99,  "Hardware",  25),
        ("SIEM Dashboard Pro",         "Security information & event management platform",        8999.00, "Software",  35),
    ]
    c.executemany(
        "INSERT INTO products (name, description, price, category, stock) VALUES (?, ?, ?, ?, ?)",
        products,
    )

    # ── Comments table (XSS target) ──
    c.execute("DROP TABLE IF EXISTS comments")
    c.execute("""
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    comments = [
        ("john",    "Great products! Fast shipping too."),
        ("alice",   "The Quantum Firewall is amazing, blocked 10k threats on day one!"),
        ("bob",     "Customer support was very helpful with my setup."),
        ("charlie", "Anyone tried the ThreatHunter Elite? Worth the price?"),
        ("jane",    "Love the DarkNet Monitor — found 3 leaked credentials already."),
    ]
    c.executemany(
        "INSERT INTO comments (author, message) VALUES (?, ?)",
        comments,
    )

    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {DB_PATH}")
    print(f"   → {len(users)} users, {len(products)} products, {len(comments)} comments")


if __name__ == "__main__":
    init()
