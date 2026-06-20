import {
  AlertTriangle,
  MapPin,
  Target,
  TrendingUp,
  FileText,
  Download,
  Brain,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

export interface Incident {
  id: string;
  type: string;
  sourceIP: string;
  location: string;
  riskScore: number;
  confidence: "High" | "Medium" | "Low";
  timestamp: Date;
  status: "active" | "investigating" | "resolved";
}

interface IncidentCardProps {
  incident: Incident | null;
  onViewReport: () => void;
  onDownload: () => void;
  onViewReasoning: () => void;
}

export function IncidentCard({
  incident,
  onViewReport,
  onDownload,
  onViewReasoning,
}: IncidentCardProps) {
  if (!incident) {
    return (
      <div className="bg-card border border-border rounded-lg p-6 h-full flex flex-col items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mx-auto">
            <Target className="w-8 h-8 text-muted-foreground" />
          </div>
          <p className="text-muted-foreground">No active incidents</p>
          <p className="text-xs text-muted-foreground/70">
            Run a simulation or upload logs to detect threats
          </p>
        </div>
      </div>
    );
  }

  const getSeverity = (score: number) => {
    if (score >= 80) return "critical";
    if (score >= 60) return "high";
    if (score >= 40) return "medium";
    return "safe";
  };

  const severity = getSeverity(incident.riskScore);

  const severityStyles = {
    critical: {
      bg: "bg-critical/10",
      border: "border-critical/50",
      text: "text-critical",
      label: "CRITICAL",
    },
    high: {
      bg: "bg-high/10",
      border: "border-high/50",
      text: "text-high",
      label: "HIGH",
    },
    medium: {
      bg: "bg-medium/10",
      border: "border-medium/50",
      text: "text-medium",
      label: "MEDIUM",
    },
    safe: {
      bg: "bg-safe/10",
      border: "border-safe/50",
      text: "text-safe",
      label: "LOW",
    },
  };

  const style = severityStyles[severity];

  return (
    <div
      className={cn(
        "bg-card border-2 rounded-lg overflow-hidden transition-all duration-300",
        style.border,
        severity === "critical" && "pulse-critical"
      )}
    >
      {/* Header */}
      <div className={cn("px-5 py-4", style.bg)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={cn("p-2 rounded-lg", style.bg, "border", style.border)}
            >
              <AlertTriangle className={cn("w-6 h-6", style.text)} />
            </div>
            <div>
              <span
                className={cn(
                  "text-xs font-bold tracking-wider",
                  style.text
                )}
              >
                🔴 INCIDENT DETECTED
              </span>
              <h3 className="text-lg font-bold text-foreground">
                {incident.type}
              </h3>
            </div>
          </div>
          <div
            className={cn(
              "px-3 py-1 rounded-full text-xs font-bold",
              style.bg,
              style.text,
              "border",
              style.border
            )}
          >
            {style.label}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-5 space-y-4">
        {/* Details Grid */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <Target className="w-3 h-3" /> Source IP
            </p>
            <p className="font-mono text-sm font-semibold">{incident.sourceIP}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <MapPin className="w-3 h-3" /> Location
            </p>
            <p className="text-sm font-semibold">{incident.location}</p>
          </div>
        </div>

        {/* Risk Score */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> Risk Score
            </p>
            <span className={cn("text-2xl font-bold", style.text)}>
              {incident.riskScore} / 100
            </span>
          </div>
          <Progress
            value={incident.riskScore}
            className={cn("h-2", style.bg)}
          />
        </div>

        {/* Confidence */}
        <div className="flex items-center justify-between py-2 px-3 rounded-lg bg-muted/30">
          <span className="text-sm text-muted-foreground">Confidence</span>
          <span className="font-semibold text-foreground">
            {incident.confidence}
          </span>
        </div>

        {/* Actions */}
        <div className="grid grid-cols-3 gap-1.5 md:gap-2 pt-2">
          <Button
            onClick={onViewReport}
            variant="outline"
            size="sm"
            className="gap-1.5 bg-secondary/50"
          >
            <FileText className="w-3.5 h-3.5" />
            Report
          </Button>
          <Button
            onClick={onDownload}
            variant="outline"
            size="sm"
            className="gap-1.5 bg-secondary/50"
          >
            <Download className="w-3.5 h-3.5" />
            PDF
          </Button>
          <Button
            onClick={onViewReasoning}
            variant="outline"
            size="sm"
            className="gap-1.5 bg-primary/10 border-primary/30 text-primary hover:bg-primary/20"
          >
            <Brain className="w-3.5 h-3.5" />
            AI
          </Button>
        </div>
      </div>
    </div>
  );
}
