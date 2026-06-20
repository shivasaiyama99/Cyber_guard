try:
    from crewai.tools import tool
except ImportError:
    def tool(*args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            return args[0]
        def decorator(func):
            return func
        return decorator
import pandas as pd
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
            # Read the CSV
            df = pd.read_csv('data/simulation_logs.csv')
            
            # Filter for Failed Logins
            failed_df = df[df['status'] == 'Failed_Login']
            
            # Count failures per IP
            ip_counts = failed_df['ip_address'].value_counts()
            
            # Get IPs with > 5 failures
            suspicious_ips = ip_counts[ip_counts > 5].index.tolist()
            
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