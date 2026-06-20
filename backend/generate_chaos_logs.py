import csv
import random
import os
import time
from datetime import datetime, timedelta

# --- CONFIGURATION ---
OUTPUT_DIR = "data"
OUTPUT_FILE = "simulation_logs.csv"
LOG_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

# --- CONSTANTS ---
NORMAL_IPS = [f'10.0.0.{i}' for i in range(1, 20)]
USERS = ['alice', 'bob', 'charlie', 'david', 'eve', 'frank', 'grace', 'heidi']
ENDPOINTS = ['/home', '/about', '/products', '/contact', '/login', '/dashboard', '/api/user']
METHODS = ['GET', 'POST']

# --- ATTACKERS ---
ATTACKER_A_IP = "192.168.1.55"  # The Brute Force Bot
ATTACKER_B_IP = "45.33.22.11"   # The SQL Injection Specialist
ATTACKER_C_IP = "203.0.113.8"   # The Recon Scanner

def setup_directory():
    """Creates the data directory if it doesn't exist."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 Created directory: {OUTPUT_DIR}")

def generate_normal_traffic(base_time, count=200):
    """Generates background noise (innocent users)."""
    logs = []
    for i in range(count):
        timestamp = base_time + timedelta(seconds=i*random.randint(5, 30))
        logs.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'ip_address': random.choice(NORMAL_IPS),
            'user': random.choice(USERS),
            'status': 'Success',
            'endpoint': random.choice(ENDPOINTS)
        })
    return logs

def inject_brute_force(base_time):
    """Simulates a rapid-fire Brute Force attack on the admin panel."""
    logs = []
    start_time = base_time + timedelta(minutes=10)
    
    # 30 failed attempts in 30 seconds
    for i in range(30):
        timestamp = start_time + timedelta(seconds=i)
        logs.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'ip_address': ATTACKER_A_IP,
            'user': 'admin',
            'status': 'Failed_Login',  # This keyword triggers the Sentry
            'endpoint': '/admin/login'
        })
    return logs

def inject_sql_injection(base_time):
    """Simulates sophisticated SQL Injection attempts."""
    logs = []
    start_time = base_time + timedelta(minutes=25)
    
    payloads = [
        '/products?id=1 OR 1=1',
        '/login?user=admin\' --',
        '/api/v1/users?id=1; DROP TABLE logs',
        '/search?q=\' UNION SELECT username, password FROM users --'
    ]
    
    for i, payload in enumerate(payloads):
        timestamp = start_time + timedelta(seconds=i*45) # Slower, more stealthy
        logs.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'ip_address': ATTACKER_B_IP,
            'user': 'unknown',
            'status': '500_Server_Error', # SQLi often causes server crashes
            'endpoint': payload
        })
    return logs

def inject_port_scanning(base_time):
    """Simulates a vulnerability scanner looking for weak points."""
    logs = []
    start_time = base_time + timedelta(minutes=5)
    
    scan_targets = [
        '/wp-admin', '/.env', '/backup.zip', '/id_rsa', '/config.php', 
        '/phpmyadmin', '/shell.php', '/test.sql'
    ]
    
    for i, target in enumerate(scan_targets):
        timestamp = start_time + timedelta(seconds=i*2) # Very fast scanning
        logs.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'ip_address': ATTACKER_C_IP,
            'user': '-',
            'status': '404_Not_Found', # Triggers the Sentry's scanner detection
            'endpoint': target
        })
    return logs

def main():
    print("🚀 Initializing Cyber Range Simulator...")
    setup_directory()
    
    base_time = datetime.now() - timedelta(hours=1)
    
    # 1. Generate Layers
    print("Generating background traffic...")
    all_logs = generate_normal_traffic(base_time)
    
    print(f"Injecting Brute Force Attack from {ATTACKER_A_IP}...")
    all_logs.extend(inject_brute_force(base_time))
    
    print(f"Injecting SQL Injection Attack from {ATTACKER_B_IP}...")
    all_logs.extend(inject_sql_injection(base_time))
    
    print(f"Injecting Reconnaissance Scan from {ATTACKER_C_IP}...")
    all_logs.extend(inject_port_scanning(base_time))
    
    # 2. Sort logs by time (to simulate reality)
    all_logs.sort(key=lambda x: x['timestamp'])
    
    # 3. Write to File
    print(f"\n💾 Saving data to {LOG_PATH}...")
    with open(LOG_PATH, 'w', newline='') as f:
        fieldnames = ['timestamp', 'ip_address', 'user', 'status', 'endpoint']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_logs)
        
    print(f"\n✅ SIMULATION COMPLETE. {len(all_logs)} log entries created.")
    print("The Cyberguard Agents are ready to hunt.")

if __name__ == "__main__":
    main()