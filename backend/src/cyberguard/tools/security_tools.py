try:
    from crewai.tools import tool
except ImportError:
    def tool(*args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            return args[0]
        def decorator(func):
            return func
        return decorator
import csv
import json
import os

class SecurityTools:

    @tool("Log Scanner")
    def scan_logs_for_failures():
        """
        Reads the 'data/simulation_logs.csv' file and identifies IP addresses 
        that have more than 5 failed login attempts.
        Returns a list of suspicious IPs.
        """
        try:
            suspicious_ips = []
            ip_counts = {}
            # Read the CSV using built-in csv module
            with open('data/simulation_logs.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('status') == 'Failed_Login':
                        ip = row.get('ip_address')
                        if ip:
                            ip_counts[ip] = ip_counts.get(ip, 0) + 1
            
            # Get IPs with > 5 failures
            suspicious_ips = [ip for ip, count in ip_counts.items() if count > 5]
            
            return f"Suspicious IPs found with >5 failures: {suspicious_ips}"
        except Exception as e:
            return f"Error reading logs: {str(e)}"

    @tool("Threat Intel Lookup")
    def check_threat_db(ip_address: str):
        """
        Checks a specific IP address against the 'data/threat_db.json' database.
        Returns the reputation (Safe/Malicious) and details.
        """
        try:
            with open('data/threat_db.json', 'r') as f:
                threat_db = json.load(f)
            
            # Clean the input (remove quotes if agent adds them)
            ip_clean = ip_address.strip().replace("'", "").replace('"', "")
            
            if ip_clean in threat_db:
                return f"THREAT MATCH FOUND: {threat_db[ip_clean]}"
            else:
                return f"IP {ip_clean} is not in the threat database (Assume Safe)."
        except Exception as e:
            return f"Error checking threat DB: {str(e)}"