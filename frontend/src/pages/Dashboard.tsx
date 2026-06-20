import { useEffect, useState, useMemo, useRef } from "react";
import {
  AlertTriangle,
  Activity,
  Database,
  Bot,
  Clock,
  FileSearch,
  ListChecks,
  MessageSquare,
  Shield,
} from "lucide-react";
import { StatCard } from "@/components/dashboard/StatCard";
import { ControlPanel } from "@/components/dashboard/ControlPanel";
import { AgentFeed } from "@/components/dashboard/AgentFeed";
import { IncidentCard } from "@/components/dashboard/IncidentCard";
import { useNavigate } from "react-router-dom";
import { useBackend } from "@/hooks/useBackend";
import {
  fetchStructuredReport,
  getLlmStatus,
  getAnomalyReport,
  getIncidents,
  type StructuredReport,
  type LlmStatus,
  type AnomalyReport,
} from "@/lib/api";
import type { Incident } from "@/components/dashboard/IncidentCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

function mapStructuredToIncident(s: StructuredReport | null): Incident | null {
  if (!s) return null;
  const hasData =
    s.risk_score != null ||
    s.attack_type ||
    s.source_ip ||
    s.incident_id ||
    (s.recommended_actions && s.recommended_actions.length > 0);
  if (!hasData) return null;
  const score = s.risk_score != null ? parseInt(s.risk_score, 10) : 0;
  const severity = (s.severity || "").toUpperCase();
  const confidence: "High" | "Medium" | "Low" =
    severity.includes("HIGH") || severity.includes("CRITICAL")
      ? "High"
      : severity.includes("MEDIUM")
        ? "Medium"
        : "Low";
  return {
    id: s.incident_id || "report",
    type: s.attack_type || "Security incident",
    sourceIP: s.source_ip || "N/A",
    location: "N/A",
    riskScore: Number.isNaN(score) ? 0 : score,
    confidence,
    timestamp: new Date(),
    status: "investigating",
  };
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { status, agentLogs, start, reset } = useBackend();
  const [structured, setStructured] = useState<StructuredReport | null>(null);
  const [llmStatus, setLlmStatus] = useState<LlmStatus | null>(null);
  const [anomalyReport, setAnomalyReport] = useState<AnomalyReport | null>(null);
  const [activeIncidents, setActiveIncidents] = useState(0);
  const prevStatusRef = useRef<string>(status);

  // Fetch structured report when status is idle or complete
  useEffect(() => {
    const prevStatus = prevStatusRef.current;
    prevStatusRef.current = status;

    // Detect completion transitions
    const justFinished =
      (prevStatus === "running" && status === "idle") ||
      (prevStatus === "running" && status === "complete") ||
      (prevStatus === "complete" && status === "idle");

    if (status === "running") {
      setStructured(null);
      return;
    }

    // Fetch on idle, complete, or after a completion transition
    if (status === "idle" || status === "complete" || justFinished) {
      let mounted = true;

      const fetchData = () => {
        fetchStructuredReport()
          .then((data) => {
            console.log('fetchStructuredReport response:', data);
            if (mounted) setStructured(data && Object.keys(data).length > 0 ? data : null);
          })
          .catch((e) => {
            console.error("fetchStructuredReport error:", e);
          });

        // Fetch incidents count from MongoDB
        getIncidents()
          .then((incidents) => {
            if (mounted && incidents && incidents.length > 0) {
              setActiveIncidents(incidents.length);
            }
          })
          .catch(() => {});
      };

      fetchData();

      const id = setInterval(() => {
        fetchData();
      }, 5000);

      return () => {
        mounted = false;
        clearInterval(id);
      };
    }
  }, [status]);

  // Fetch LLM status on mount
  useEffect(() => {
    getLlmStatus().then(setLlmStatus).catch(() => {});
  }, []);

  // Fetch anomaly report on mount and after each simulation
  useEffect(() => {
    getAnomalyReport().then(setAnomalyReport).catch(() => {});
  }, [status]);

  const incident = useMemo(() => mapStructuredToIncident(structured), [structured]);
  const isInvestigating = status === "running";

  // Use the larger of: incident-derived count vs MongoDB incidents count
  const displayActiveIncidents = incident ? Math.max(1, activeIncidents) : activeIncidents;
  const riskLevel = incident?.riskScore ?? (structured?.risk_score != null ? parseInt(String(structured.risk_score), 10) : 0);

  return (
    <div className="p-3 md:p-6 space-y-4 md:space-y-6">
      {/* Header badges: LLM Backend */}
      <div className="flex items-center gap-2 md:gap-3 flex-wrap">
        {llmStatus && (
          <Badge
            variant="secondary"
            className={
              llmStatus.backend === "ollama"
                ? "bg-green-500/20 text-green-400 border-green-500/30"
                : "bg-blue-500/20 text-blue-400 border-blue-500/30"
            }
          >
            LLM: {llmStatus.backend} ({llmStatus.model})
          </Badge>
        )}
      </div>

      {/* System Overview Cards */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Incidents"
          value={displayActiveIncidents}
          icon={AlertTriangle}
          severity={displayActiveIncidents > 0 ? "critical" : "safe"}
          subtitle={displayActiveIncidents > 0 ? "Requires attention" : "All clear"}
        />
        <StatCard
          title="Risk Level"
          value={`${riskLevel}%`}
          icon={Activity}
          severity={
            riskLevel >= 80
              ? "critical"
              : riskLevel >= 60
                ? "high"
                : riskLevel >= 40
                  ? "medium"
                  : "safe"
          }
          subtitle={
            riskLevel >= 80
              ? "Critical threat"
              : riskLevel >= 60
              ? "High risk"
              : riskLevel >= 40
              ? "Moderate"
              : "Low risk"
          }
        />
        <StatCard
          title="Logs Analyzed"
          value={agentLogs.length.toLocaleString()}
          icon={Database}
          severity="default"
          subtitle="This session"
        />
        <StatCard
          title="Backend Status"
          value={status === "running" ? "Running" : status === "complete" ? "Complete" : "Idle"}
          icon={Bot}
          severity={status === "running" ? "medium" : status === "complete" ? "safe" : "safe"}
          subtitle={status === "running" ? "Processing" : status === "complete" ? "Investigation done" : "Ready"}
        />
      </section>

      {/* Anomaly Detection Panel */}
      {anomalyReport && (
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Anomaly Detection
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 flex-wrap">
              <span className="text-sm text-muted-foreground">
                Anomalous IPs: <span className="font-bold text-foreground">{anomalyReport.anomalous_count}</span>
              </span>
              {anomalyReport.anomalous_ips.map((ip) => (
                <Badge
                  key={ip}
                  variant="secondary"
                  className="bg-red-500/20 text-red-400 border-red-500/30"
                >
                  {ip}
                </Badge>
              ))}
              {anomalyReport.anomalous_count === 0 && (
                <Badge variant="secondary" className="bg-safe/20 text-safe border-safe/30">
                  All Clear
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Control Panel */}
        <div className="lg:col-span-3">
          <ControlPanel
            onSimulate={(_attackType: string) => {
              start();
            }}
            onStartInvestigation={() => start()}
            onReset={() => {
              reset();
              setStructured(null);
              setAnomalyReport(null);
              setActiveIncidents(0);
            }}
            isInvestigating={isInvestigating}
          />
        </div>


        {/* Live Agent Feed */}
        <div className="lg:col-span-5 h-[400px] md:h-[580px]">
          <AgentFeed logs={agentLogs} />
        </div>


        {/* Incident Summary + Incident Dashboard */}
        <div className="lg:col-span-4 space-y-4">
          <IncidentCard
            incident={incident}
            onViewReport={() => navigate("/report")}
            onDownload={() => {}}
            onViewReasoning={() => navigate("/investigation")}
          />

          {/* Incident Dashboard: Timeline, Evidence, Risk, Actions, Agent Notes */}
          {(structured &&
            (structured.timeline?.length ||
              structured.evidence ||
              structured.risk_score != null ||
              (structured.recommended_actions && structured.recommended_actions.length > 0) ||
              (structured.agent_notes && structured.agent_notes.length > 0))) && (
            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Incident Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Risk score & severity badge */}
                {(structured.risk_score != null || structured.severity) && (
                  <div className="flex flex-wrap items-center gap-2">
                    {structured.risk_score != null && (
                      <span className="text-2xl font-bold text-foreground">
                        Risk: {structured.risk_score}/100
                      </span>
                    )}
                    {structured.severity && (
                      <Badge
                        variant="secondary"
                        className={
                          String(structured.severity).toUpperCase().includes("HIGH") ||
                          String(structured.severity).toUpperCase().includes("CRITICAL")
                            ? "bg-high/20 text-high border-high/30"
                            : String(structured.severity).toUpperCase().includes("MEDIUM")
                              ? "bg-medium/20 text-medium border-medium/30"
                              : "bg-safe/20 text-safe border-safe/30"
                        }
                      >
                        {structured.severity}
                      </Badge>
                    )}
                  </div>
                )}

                {/* Timeline */}
                {structured.timeline && structured.timeline.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                      <Clock className="w-4 h-4" />
                      Timeline
                    </div>
                    <ScrollArea className="h-32 rounded-md border border-border p-2">
                      <ul className="space-y-1.5 text-sm">
                        {structured.timeline.map((e, i) => (
                          <li key={i} className="flex gap-2">
                            <span className="font-mono text-muted-foreground shrink-0">
                              {e.time}
                            </span>
                            <span className="text-foreground">{e.event}</span>
                          </li>
                        ))}
                      </ul>
                    </ScrollArea>
                  </div>
                )}

                {/* Evidence */}
                {structured.evidence && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                      <FileSearch className="w-4 h-4" />
                      Evidence
                    </div>
                    <div className="rounded-md border border-border p-3 bg-muted/20 text-sm whitespace-pre-wrap">
                      {structured.evidence}
                    </div>
                  </div>
                )}

                {/* Recommended actions */}
                {structured.recommended_actions && structured.recommended_actions.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                      <ListChecks className="w-4 h-4" />
                      Recommended Actions
                    </div>
                    <ul className="list-disc pl-5 space-y-1 text-sm text-muted-foreground">
                      {structured.recommended_actions.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* AI Agent notes */}
                {structured.agent_notes && structured.agent_notes.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                      <MessageSquare className="w-4 h-4" />
                      AI Agent Notes
                    </div>
                    <div className="space-y-2">
                      {structured.agent_notes.map((n, i) => (
                        <div
                          key={i}
                          className="rounded-md border border-border p-2 bg-primary/5"
                        >
                          <span className="text-xs font-semibold text-primary">
                            [{n.agent}]
                          </span>
                          <p className="text-sm text-muted-foreground mt-0.5">
                            {n.note}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </section>
    </div>
  );
}
