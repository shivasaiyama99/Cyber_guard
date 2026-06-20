import { Bot, Shield, Search, Scale, Stethoscope, PenTool, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

const agents = [
  {
    name: "SENTRY",
    role: "Log Monitor",
    description: "Continuously monitors all incoming logs and system events for anomalies",
    icon: Shield,
    color: "text-primary",
    bgColor: "bg-primary/10",
    borderColor: "border-primary/30",
  },
  {
    name: "HUNTER",
    role: "Threat Intelligence",
    description: "Cross-references events with threat databases and known attack signatures",
    icon: Search,
    color: "text-high",
    bgColor: "bg-high/10",
    borderColor: "border-high/30",
  },
  {
    name: "DETECTIVE",
    role: "Pattern Analyzer",
    description: "Uses ML models to identify attack patterns and classify threat types",
    icon: Search,
    color: "text-medium",
    bgColor: "bg-medium/10",
    borderColor: "border-medium/30",
  },
  {
    name: "JUDGE",
    role: "Risk Assessor",
    description: "Computes risk scores based on threat severity, asset value, and exposure",
    icon: Scale,
    color: "text-critical",
    bgColor: "bg-critical/10",
    borderColor: "border-critical/30",
  },
  {
    name: "MEDIC",
    role: "Remediation Expert",
    description: "Generates actionable remediation steps and automates response actions",
    icon: Stethoscope,
    color: "text-safe",
    bgColor: "bg-safe/10",
    borderColor: "border-safe/30",
  },
  {
    name: "SCRIBE",
    role: "Report Generator",
    description: "Creates detailed incident reports with timeline, evidence, and recommendations",
    icon: PenTool,
    color: "text-accent",
    bgColor: "bg-accent/10",
    borderColor: "border-accent/30",
  },
];

export default function Investigation() {
  return (
    <div className="p-3 md:p-6 space-y-6 md:space-y-8">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-xl md:text-2xl font-bold text-foreground">Investigation Pipeline</h1>
        <p className="text-muted-foreground">
          Autonomous AI agents work together to detect, analyze, and respond to security threats
        </p>
      </div>

      {/* Agent Flow Diagram */}
      <div className="bg-card border border-border rounded-lg p-4 md:p-6">
        <h2 className="text-lg font-semibold text-foreground mb-4 md:mb-6">Agent Workflow</h2>
        
        <div className="flex flex-wrap items-center justify-center gap-4">
          {agents.map((agent, index) => (
            <div key={agent.name} className="flex items-center gap-4">
              <div
                className={cn(
                  "relative p-4 rounded-xl border-2 transition-all duration-300 hover:scale-105",
                  agent.bgColor,
                  agent.borderColor
                )}
              >
                <div className="flex flex-col items-center text-center space-y-2">
                  <div className={cn("p-3 rounded-lg", agent.bgColor)}>
                    <agent.icon className={cn("w-6 h-6", agent.color)} />
                  </div>
                  <div>
                    <p className={cn("font-bold text-sm", agent.color)}>{agent.name}</p>
                    <p className="text-xs text-muted-foreground">{agent.role}</p>
                  </div>
                </div>
              </div>
              
              {index < agents.length - 1 && (
                <ArrowRight className="w-5 h-5 text-muted-foreground hidden lg:block" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Agent Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <div
            key={agent.name}
            className={cn(
              "p-5 rounded-lg border-2 transition-all duration-300 hover:shadow-lg card-glow",
              agent.bgColor,
              agent.borderColor
            )}
          >
            <div className="flex items-start gap-4">
              <div className={cn("p-3 rounded-lg flex-shrink-0", agent.bgColor)}>
                <agent.icon className={cn("w-6 h-6", agent.color)} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className={cn("font-bold", agent.color)}>{agent.name}</h3>
                  <span className="text-xs text-muted-foreground">• {agent.role}</span>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {agent.description}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* How It Works */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold text-foreground mb-4">How It Works</h2>
        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold flex-shrink-0">
              1
            </div>
            <div>
              <h4 className="font-semibold text-foreground">Log Ingestion</h4>
              <p className="text-sm text-muted-foreground">
                SENTRY continuously monitors authentication logs, network traffic, and system events
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold flex-shrink-0">
              2
            </div>
            <div>
              <h4 className="font-semibold text-foreground">Threat Detection</h4>
              <p className="text-sm text-muted-foreground">
                HUNTER and DETECTIVE analyze suspicious patterns using threat intelligence and ML models
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold flex-shrink-0">
              3
            </div>
            <div>
              <h4 className="font-semibold text-foreground">Risk Assessment</h4>
              <p className="text-sm text-muted-foreground">
                JUDGE evaluates the severity and potential impact, computing a risk score
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold flex-shrink-0">
              4
            </div>
            <div>
              <h4 className="font-semibold text-foreground">Response & Documentation</h4>
              <p className="text-sm text-muted-foreground">
                MEDIC generates remediation actions while SCRIBE creates comprehensive incident reports
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
