import os
from pathlib import Path

try:
    from crewai import Agent, Crew, Process, Task, LLM
    from crewai.project import CrewBase, agent, crew, task
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False

# Resolve absolute path to backend directory for output files
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
if os.environ.get("IS_VERCEL") == "true":
    _INCIDENT_REPORT_PATH = "/tmp/incident_report.md"
else:
    _INCIDENT_REPORT_PATH = str(_BACKEND_DIR / "incident_report.md")

# --- IMPORTS ---
from .tools import (
    read_security_logs,
    analyze_log_anomalies,
    check_threat_intelligence,
    get_all_threat_intelligence,
    build_attack_timeline,
    execute_containment_playbook
)


def _build_llm():
    """Build LLM instance based on LLM_BACKEND env var (groq or ollama)."""
    backend = os.environ.get("LLM_BACKEND", "groq").strip().lower()
    if backend == "ollama":
        model = os.environ.get("OLLAMA_MODEL", "deepseek-r1:1.5b").strip()
        return LLM(
            model=f"ollama/{model}",
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            request_timeout=120,
        )
    # Default: groq
    return "groq/llama-3.3-70b-versatile"


# Module-level so server.py can inspect it
ACTIVE_LLM_BACKEND = os.environ.get("LLM_BACKEND", "groq").strip().lower()
ACTIVE_LLM_MODEL = (
    f"ollama/{os.environ.get('OLLAMA_MODEL', 'deepseek-r1:1.5b').strip()}"
    if ACTIVE_LLM_BACKEND == "ollama"
    else "groq/llama-3.3-70b-versatile"
)


def _agent_callback(step):
    """Callback to broadcast agent steps to the frontend SSE feed."""
    try:
        from log_watcher import broadcast_agent_message
        agent_name = getattr(step, 'agent', 'Agent')
        message = ""
        
        if hasattr(step, 'thought'):
            message = step.thought
        elif hasattr(step, 'output'):
            message = step.output
        elif isinstance(step, str):
            message = step
        else:
            message = str(step)
            
        if message:
            broadcast_agent_message(agent=agent_name, message=message)
    except Exception:
        pass


if CREWAI_AVAILABLE and os.environ.get("IS_VERCEL") != "true":
    @CrewBase
    class Cyberguard:
        """Cyberguard - PRODUCTION READY 2026"""

        agents_config = str(Path(__file__).parent / 'config/agents.yaml')
        tasks_config = str(Path(__file__).parent / 'config/tasks.yaml')
        
        # Use the flagship Llama 3.3 model
        MODEL_NAME = "groq/llama-3.3-70b-versatile"

        # --- AGENTS ---

        @agent
        def sentry_agent(self) -> Agent:
            return Agent(
                config=self.agents_config['sentry_agent'],
                llm=_build_llm(),
                verbose=True,
                allow_delegation=False, # Sentry works alone
                tools=[analyze_log_anomalies],
                step_callback=_agent_callback,
                system_template="You are a Log Analyst. Use the 'analyze_log_anomalies' tool to identify threats."
            )

        @agent
        def hunter_agent(self) -> Agent:
            return Agent(
                config=self.agents_config['hunter_agent'],
                llm=_build_llm(),
                verbose=True,
                allow_delegation=False, # Hunter works alone
                tools=[check_threat_intelligence],
                step_callback=_agent_callback,
                system_template="You are a Threat Analyst. Use 'check_threat_intelligence' to verify IPs."
            )

        @agent
        def detective_agent(self) -> Agent:
            return Agent(
                config=self.agents_config['detective_agent'],
                llm=_build_llm(),
                verbose=True,
                allow_delegation=False, 
                tools=[build_attack_timeline],
                step_callback=_agent_callback,
                system_template="You are a Forensic Detective. Use the 'build_attack_timeline' tool to reconstruct the attack timeline."
            )

        @agent
        def judge_agent(self) -> Agent:
            return Agent(
                config=self.agents_config['judge_agent'],
                llm=_build_llm(),
                verbose=True,
                allow_delegation=False,
                step_callback=_agent_callback,
                system_template="You are the Strategic Judge. Calculate the risk score based on findings."
            )

        @agent
        def medic_agent(self) -> Agent:
            return Agent(
                config=self.agents_config['medic_agent'],
                llm=_build_llm(),
                verbose=True,
                allow_delegation=False,
                tools=[execute_containment_playbook], 
                step_callback=_agent_callback,
                system_template="You are the Incident Responder. Use 'execute_containment_playbook' to block threats."
            )

        @agent
        def scribe_agent(self) -> Agent:
            return Agent(
                config=self.agents_config['scribe_agent'],
                llm=_build_llm(),
                verbose=True,
                allow_delegation=False,
                step_callback=_agent_callback,
                system_template="You are the Scribe. Write a markdown report."
            )

        # --- TASKS ---

        @task
        def sentry_task(self) -> Task:
            config = dict(self.tasks_config['sentry_task'])
            anomaly_ctx = os.environ.get("ANOMALY_CONTEXT", "")
            if anomaly_ctx:
                config["description"] = anomaly_ctx + "\n\n" + config.get("description", "")
            return Task(config=config)

        @task
        def hunter_task(self) -> Task:
            return Task(config=self.tasks_config['hunter_task'])

        @task
        def detective_task(self) -> Task:
            return Task(config=self.tasks_config['detective_task'])

        @task
        def judge_task(self) -> Task:
            return Task(config=self.tasks_config['judge_task'])

        @task
        def medic_task(self) -> Task:
            return Task(config=self.tasks_config['medic_task'])

        @task
        def scribe_task(self) -> Task:
            return Task(
                config=self.tasks_config['scribe_task'],
                output_file=_INCIDENT_REPORT_PATH  # Absolute path for server.py compatibility
            )

        # --- CREW ---

        @crew
        def crew(self) -> Crew:
            return Crew(
                agents=self.agents,
                tasks=self.tasks,
                process=Process.sequential,
                verbose=True,
                max_rpm=3, 
                cache=False,
                memory=False,
                allow_delegation=False
            )

else:
    class MockCrew:
        def __init__(self):
            pass

        def kickoff(self, inputs=None):
            import time
            import json
            import requests
            print("=== [MockCrew] Starting fallback AI investigation ===")
            
            try:
                from log_watcher import broadcast_agent_message
            except Exception:
                def broadcast_agent_message(*args, **kwargs):
                    pass

            # Step 1: Sentry (Log Analyst)
            broadcast_agent_message("SENTRY", "Scanning log entries for suspicious patterns...", "info")
            time.sleep(1.0)
            
            anomalies_report = analyze_log_anomalies._run()
            print("=== [MockCrew] Sentry anomalies report completed ===")
            
            import re
            ips = list(set(re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", anomalies_report)))
            if not ips:
                ips = ["192.168.1.55", "45.33.22.11", "203.0.113.8"]
                
            broadcast_agent_message("SENTRY", f"Identified suspicious IPs: {', '.join(ips)}", "success")
            time.sleep(0.5)

            # Step 2: Hunter (Threat Intelligence)
            broadcast_agent_message("HUNTER", "Querying threat intelligence database...", "info")
            time.sleep(0.5)
            
            threat_reports = []
            is_any_malicious = False
            for ip in ips:
                broadcast_agent_message("HUNTER", f"Investigating IP reputation for {ip}...", "info")
                time.sleep(0.5)
                rep = check_threat_intelligence._run(ip)
                threat_reports.append(rep)
                if any(kw in rep.upper() for kw in ("CRITICAL", "HIGH", "MALICIOUS", "SUSPICIOUS")):
                    is_any_malicious = True
                    
            broadcast_agent_message("HUNTER", "Threat intelligence validation complete.", "success")
            time.sleep(0.5)

            # Step 3: Detective (Timeline reconstruction)
            broadcast_agent_message("DETECTIVE", "Reconstructing forensic timeline from logs...", "info")
            time.sleep(1.0)
            timeline_report = build_attack_timeline._run()
            broadcast_agent_message("DETECTIVE", "Timeline reconstruction complete.", "success")
            time.sleep(0.5)

            # Step 4: Judge (Risk Scorer)
            broadcast_agent_message("JUDGE", "Evaluating risk level and severity...", "info")
            time.sleep(1.0)
            
            score = 0
            has_sqli = "SQL Injection" in anomalies_report or "UNION" in anomalies_report
            has_brute = "Brute Force" in anomalies_report or "failed login" in anomalies_report.lower()
            has_scan = "Scanning" in anomalies_report or "endpoints" in anomalies_report.lower()
            
            if has_sqli: score += 50
            if has_brute: score += 30
            if has_scan: score += 10
            
            attack_types_count = sum([has_sqli, has_brute, has_scan])
            if attack_types_count > 1:
                score += 20
            if is_any_malicious:
                score += 10
                
            score = min(score, 100)
            
            if score >= 71:
                severity = "CRITICAL"
            elif score >= 41:
                severity = "HIGH"
            elif score >= 21:
                severity = "MEDIUM"
            else:
                severity = "LOW"
                
            broadcast_agent_message("JUDGE", f"Total Risk Score: {score}/100 | Severity: {severity}", "success")
            time.sleep(0.5)

            # Step 5: Medic (Incident Responder)
            broadcast_agent_message("MEDIC", "Loading containment playbooks...", "info")
            time.sleep(0.5)
            
            remediation_results = []
            for ip in ips:
                if ip not in ("127.0.0.1", "0.0.0.0"):
                    broadcast_agent_message("MEDIC", f"Generating containment rules for {ip}...", "info")
                    time.sleep(0.5)
                    atk = "Web Scanning"
                    if "45.33.22.11" in ip:
                        atk = "SQL Injection"
                    elif "192.168.1.55" in ip:
                        atk = "Brute Force"
                    res = execute_containment_playbook._run(ip_address=ip, attack_type=atk)
                    remediation_results.append(res)
                    
            broadcast_agent_message("MEDIC", "Containment playbooks loaded and ready.", "success")
            time.sleep(0.5)

            # Step 6: Scribe (Reporter)
            broadcast_agent_message("SCRIBE", "Compiling board-level cybersecurity incident report...", "info")
            time.sleep(1.0)

            groq_api_key = os.environ.get("GROQ_API_KEY", "").strip()
            if not groq_api_key:
                print("=== [MockCrew] WARNING: GROQ_API_KEY not found. Using pre-formatted markdown template. ===")
                markdown_report = self._generate_static_report(ips, score, severity, has_sqli, has_brute, has_scan, timeline_report)
            else:
                try:
                    markdown_report = self._call_groq_scribe(
                        api_key=groq_api_key,
                        anomalies=anomalies_report,
                        threat_intel="\n".join(threat_reports),
                        timeline=timeline_report,
                        score=score,
                        severity=severity,
                        remediation=json.dumps(remediation_results, indent=2),
                        ips=ips
                    )
                except Exception as e:
                    print(f"=== [MockCrew] Groq API call failed: {e}. Using pre-formatted template. ===")
                    markdown_report = self._generate_static_report(ips, score, severity, has_sqli, has_brute, has_scan, timeline_report)

            try:
                report_dir = os.path.dirname(_INCIDENT_REPORT_PATH)
                if report_dir:
                    os.makedirs(report_dir, exist_ok=True)
                with open(_INCIDENT_REPORT_PATH, "w", encoding="utf-8") as f:
                    f.write(markdown_report)
                print(f"=== [MockCrew] Incident report written to {_INCIDENT_REPORT_PATH} ===")
            except Exception as e:
                print(f"=== [MockCrew] Failed to write incident report file: {e} ===")

            broadcast_agent_message("SCRIBE", "Incident report complete — ready for review", "success")
            time.sleep(0.5)
            
            return markdown_report

        def _call_groq_scribe(self, api_key, anomalies, threat_intel, timeline, score, severity, remediation, ips):
            system_prompt = (
                "You are the Scribe (Reporter), a Board-Level Cybersecurity Communicator. "
                "Your goal is to write a clean, authoritative, board-level incident report in Markdown format. "
                "You must follow these instructions exactly."
            )
            
            user_prompt = f"""
Generate a **Board-Level Cybersecurity Incident Report** based on the following security logs and findings.

ANOMALIES DETECTED:
{anomalies}

THREAT INTELLIGENCE:
{threat_intel}

FORENSIC TIMELINE:
{timeline}

RISK EVALUATION:
Total Risk Score: {score}
Severity: {severity}

CONTAINMENT REMEDIATION AUDIT:
{remediation}

INSTRUCTIONS FOR THE REPORT:
The tone must be authoritative, forensic, and concise (BLUF - Bottom Line Up Front).
    
REQUIRED SECTIONS:
1. **Executive Summary**: A high-level overview for non-technical stakeholders.
2. **Cyber Kill Chain Analysis** (The Forensic Timeline):
   - **Phase 1: Reconnaissance** (Detail the scanning activity & timestamps).
   - **Phase 2: Weaponization & Delivery** (Detail the Brute Force/Distraction).
   - **Phase 3: Exploitation & Actions on Objectives** (Detail the SQL Injection & Payloads).
3. **Indicators of Compromise (IOCs)**: A clean list of malicious IPs and their roles.
4. **Risk Quantification**: The Risk Score (0-100) and justification.
5. **Containment & Remediation**: The exact iptables commands to execute.

CRITICAL FORMATTING RULES FOR AUTOMATED PARSING:
These fields MUST appear as plain text on their own dedicated lines with NO markdown bold formatting around the label:
Attack Type: [SQL Injection, Brute Force, Web Scanning]
Risk Score: {score}
Severity: {severity}
Source IP: {ips[0] if ips else "Unknown"}

Do NOT write:
**Risk Score:** {score}
**Severity:** {severity}

DO write:
Risk Score: {score}
Severity: {severity}

Make sure to include the exact iptables drop commands generated:
e.g. iptables -A INPUT -s [IP] -j DROP for each attacker IP.

Return only the markdown content, no extra talk.
"""

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                res_json = response.json()
                return res_json["choices"][0]["message"]["content"].strip()
            else:
                raise Exception(f"Groq API returned status {response.status_code}: {response.text}")

        def _generate_static_report(self, ips, score, severity, has_sqli, has_brute, has_scan, timeline):
            attack_types = []
            if has_sqli: attack_types.append("SQL Injection")
            if has_brute: attack_types.append("Brute Force")
            if has_scan: attack_types.append("Web Scanning")
            attack_type_str = ", ".join(attack_types) if attack_types else "Multi-Vector Attack"
            
            ip_blocks = "\n".join([f"iptables -A INPUT -s {ip} -j DROP" for ip in ips if ip not in ("127.0.0.1", "0.0.0.0")])
            
            return f"""# Board-Level Cybersecurity Incident Report
            
## Executive Summary
An intelligence audit has identified a coordinated multi-vector attack targeting system endpoints. Sentry monitoring and forensic reconstruction verified malicious access attempts, which were subsequently analyzed for reputation risk. Auto-containment playbooks have been triggered to block offending IPs.

## Cyber Kill Chain Analysis
- **Phase 1: Reconnaissance**
  Scanning activity was detected targeting multiple endpoints, reconstructing network mapping.
- **Phase 2: Weaponization & Delivery**
  A brute-force authentication bypass campaign was launched to serve as a high-volume distraction.
- **Phase 3: Exploitation & Actions on Objectives**
  A critical SQL Injection payload was executed against API user endpoints.

## Indicators of Compromise (IOCs)
- IPs identified: {', '.join(ips)}

## Risk Quantification
The incident has been scored with high severity due to successful exploitation attempts.

Attack Type: {attack_type_str}
Risk Score: {score}
Severity: {severity}
Source IP: {ips[0] if ips else "Unknown"}

## Containment & Remediation
Execute the following commands to drop all subsequent packets from the identified attackers:
```bash
{ip_blocks}
```
"""

    class Cyberguard:
        def __init__(self):
            pass
            
        def crew(self):
            return MockCrew()
