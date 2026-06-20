import { useState, useCallback } from "react";
import { AgentLog } from "@/components/dashboard/AgentFeed";
import { Incident } from "@/components/dashboard/IncidentCard";

const attackSimulations: Record<
  string,
  { logs: Omit<AgentLog, "id" | "timestamp">[]; incident: Omit<Incident, "id" | "timestamp"> }
> = {
  "ssh-brute-force": {
    logs: [
      { agent: "SENTRY", message: "Scanning authentication logs...", type: "info" },
      { agent: "SENTRY", message: "Detected 847 failed login attempts in 5 minutes", type: "warning" },
      { agent: "HUNTER", message: "IP 192.168.1.55 found in threat intelligence database", type: "warning" },
      { agent: "HUNTER", message: "Cross-referencing with known botnet signatures...", type: "info" },
      { agent: "DETECTIVE", message: "Pattern analysis: SSH Brute Force Attack confirmed", type: "error" },
      { agent: "DETECTIVE", message: "Attack vector: Password dictionary attack", type: "info" },
      { agent: "JUDGE", message: "Computing risk score based on threat indicators...", type: "info" },
      { agent: "JUDGE", message: "Risk Score computed: 92/100 (CRITICAL)", type: "error" },
      { agent: "MEDIC", message: "Generating recommended actions...", type: "info" },
      { agent: "MEDIC", message: "ACTION: Block IP at firewall, Reset compromised credentials", type: "success" },
      { agent: "SCRIBE", message: "Incident report created and ready for review", type: "success" },
    ],
    incident: {
      type: "SSH Brute Force Attack",
      sourceIP: "192.168.1.55",
      location: "Moscow, Russia (Simulated)",
      riskScore: 92,
      confidence: "High",
      status: "active",
    },
  },
  "sql-injection": {
    logs: [
      { agent: "SENTRY", message: "Monitoring web application logs...", type: "info" },
      { agent: "SENTRY", message: "Suspicious query pattern detected in request payload", type: "warning" },
      { agent: "HUNTER", message: "Analyzing request origin: 10.0.0.42", type: "info" },
      { agent: "HUNTER", message: "Request contains SQL metacharacters: ' OR 1=1 --", type: "warning" },
      { agent: "DETECTIVE", message: "SQL Injection attempt identified", type: "error" },
      { agent: "DETECTIVE", message: "Target: /api/users endpoint, Parameter: user_id", type: "info" },
      { agent: "JUDGE", message: "Assessing database exposure risk...", type: "info" },
      { agent: "JUDGE", message: "Risk Score: 78/100 (HIGH) - Potential data breach", type: "error" },
      { agent: "MEDIC", message: "Recommended: Sanitize inputs, Enable WAF rules", type: "success" },
      { agent: "SCRIBE", message: "Generating forensic timeline...", type: "info" },
      { agent: "SCRIBE", message: "Incident documented with full request trace", type: "success" },
    ],
    incident: {
      type: "SQL Injection Attempt",
      sourceIP: "10.0.0.42",
      location: "Internal Network",
      riskScore: 78,
      confidence: "High",
      status: "active",
    },
  },
  "suspicious-login": {
    logs: [
      { agent: "SENTRY", message: "User authentication event detected", type: "info" },
      { agent: "SENTRY", message: "Login from new geographic location", type: "warning" },
      { agent: "HUNTER", message: "User: admin@company.com, IP: 203.45.67.89", type: "info" },
      { agent: "HUNTER", message: "Previous logins: New York, USA | Current: Lagos, Nigeria", type: "warning" },
      { agent: "DETECTIVE", message: "Impossible travel detected: 12,000km in 30 minutes", type: "error" },
      { agent: "DETECTIVE", message: "Checking for VPN/Proxy indicators...", type: "info" },
      { agent: "JUDGE", message: "Risk Score: 65/100 (HIGH) - Account compromise likely", type: "warning" },
      { agent: "MEDIC", message: "ACTION: Force MFA re-authentication, Notify user", type: "success" },
      { agent: "SCRIBE", message: "Alert escalated to security team", type: "success" },
    ],
    incident: {
      type: "Suspicious Login Activity",
      sourceIP: "203.45.67.89",
      location: "Lagos, Nigeria",
      riskScore: 65,
      confidence: "Medium",
      status: "investigating",
    },
  },
  "malware-detected": {
    logs: [
      { agent: "SENTRY", message: "Endpoint protection alert received", type: "warning" },
      { agent: "SENTRY", message: "Suspicious process execution on WORKSTATION-042", type: "warning" },
      { agent: "HUNTER", message: "File hash: a3f2b7c8... matches known ransomware", type: "error" },
      { agent: "HUNTER", message: "Malware family identified: LockBit 3.0", type: "error" },
      { agent: "DETECTIVE", message: "Tracing infection vector: Phishing email attachment", type: "info" },
      { agent: "DETECTIVE", message: "Lateral movement detected to 3 additional hosts", type: "error" },
      { agent: "JUDGE", message: "CRITICAL ALERT: Active ransomware outbreak", type: "error" },
      { agent: "JUDGE", message: "Risk Score: 98/100 - Immediate action required", type: "error" },
      { agent: "MEDIC", message: "ISOLATING affected systems from network", type: "success" },
      { agent: "MEDIC", message: "Initiating backup restoration procedures", type: "success" },
      { agent: "SCRIBE", message: "Incident response playbook activated", type: "success" },
    ],
    incident: {
      type: "Ransomware Attack (LockBit 3.0)",
      sourceIP: "WORKSTATION-042",
      location: "Corporate Network",
      riskScore: 98,
      confidence: "High",
      status: "active",
    },
  },
  "data-exfiltration": {
    logs: [
      { agent: "SENTRY", message: "Unusual outbound data transfer detected", type: "warning" },
      { agent: "SENTRY", message: "500MB transferred to external IP in 10 minutes", type: "warning" },
      { agent: "HUNTER", message: "Destination: 45.77.123.45 (Unregistered VPS)", type: "info" },
      { agent: "HUNTER", message: "Protocol: HTTPS with encrypted payload", type: "info" },
      { agent: "DETECTIVE", message: "Source identified: Finance server (FS-PROD-01)", type: "warning" },
      { agent: "DETECTIVE", message: "Data classification: PII, Financial records", type: "error" },
      { agent: "JUDGE", message: "Risk Score: 88/100 - Data breach in progress", type: "error" },
      { agent: "MEDIC", message: "Blocking outbound connection...", type: "success" },
      { agent: "MEDIC", message: "Initiating DLP incident response", type: "success" },
      { agent: "SCRIBE", message: "Regulatory notification template prepared", type: "success" },
    ],
    incident: {
      type: "Data Exfiltration Attempt",
      sourceIP: "45.77.123.45",
      location: "Unknown (VPS)",
      riskScore: 88,
      confidence: "High",
      status: "active",
    },
  },
};

export function useSimulation() {
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [logsAnalyzed, setLogsAnalyzed] = useState(0);

  const simulateAttack = useCallback((attackType: string) => {
    const simulation = attackSimulations[attackType];
    if (!simulation) return;

    setIsInvestigating(true);
    setLogs([]);
    setIncident(null);

    let logIndex = 0;
    const interval = setInterval(() => {
      if (logIndex < simulation.logs.length) {
        const log = simulation.logs[logIndex];
        setLogs((prev) => [
          ...prev,
          {
            ...log,
            id: `log-${Date.now()}-${logIndex}`,
            timestamp: new Date(),
          },
        ]);
        setLogsAnalyzed((prev) => prev + Math.floor(Math.random() * 500) + 100);
        logIndex++;
      } else {
        clearInterval(interval);
        setIncident({
          ...simulation.incident,
          id: `incident-${Date.now()}`,
          timestamp: new Date(),
        });
      }
    }, 800);
  }, []);

  const startInvestigation = useCallback(() => {
    if (logs.length === 0) {
      // Demo mode - run a random simulation
      const attacks = Object.keys(attackSimulations);
      const randomAttack = attacks[Math.floor(Math.random() * attacks.length)];
      simulateAttack(randomAttack);
    }
  }, [logs.length, simulateAttack]);

  const reset = useCallback(() => {
    setLogs([]);
    setIncident(null);
    setIsInvestigating(false);
    setLogsAnalyzed(0);
  }, []);

  return {
    logs,
    incident,
    isInvestigating,
    logsAnalyzed,
    simulateAttack,
    startInvestigation,
    reset,
  };
}
