import {
  Shield,
  Cpu,
  Database,
  Zap,
  Users,
  Lock,
  GitBranch,
  Layers,
} from "lucide-react";
import { cn } from "@/lib/utils";

const features = [
  {
    icon: Cpu,
    title: "Autonomous Agents",
    description: "6 specialized AI agents work in concert to detect, analyze, and respond to threats",
  },
  {
    icon: Zap,
    title: "Real-time Detection",
    description: "Continuous monitoring with sub-second response times for critical threats",
  },
  {
    icon: Database,
    title: "Threat Intelligence",
    description: "Integrated with global threat databases for up-to-date attack signatures",
  },
  {
    icon: Lock,
    title: "Automated Response",
    description: "AI-generated remediation actions with optional automated execution",
  },
];

const techStack = [
  { name: "React", category: "Frontend" },
  { name: "TypeScript", category: "Language" },
  { name: "Tailwind CSS", category: "Styling" },
  { name: "LangChain", category: "AI Framework" },
  { name: "OpenAI GPT-4", category: "LLM" },
  { name: "Python", category: "Backend" },
];

export default function About() {
  return (
    <div className="p-3 md:p-6 max-w-4xl mx-auto space-y-6 md:space-y-8">
      {/* Hero */}
      <div className="text-center space-y-4">
        <div className="inline-flex items-center justify-center w-16 h-16 md:w-20 md:h-20 rounded-2xl bg-primary/10 border border-primary/30 mb-4">
          <Shield className="w-8 h-8 md:w-10 md:h-10 text-primary" />
        </div>
        <h1 className="text-2xl md:text-3xl font-bold text-gradient-cyber">CyberGuard</h1>
        <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
          An Autonomous Security Operations Center powered by AI Agents
        </p>
      </div>

      {/* What is CyberGuard */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-xl font-semibold text-foreground mb-4">What is CyberGuard?</h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          CyberGuard is a next-generation Security Operations Center (SOC) that leverages 
          autonomous AI agents to detect, investigate, and respond to cybersecurity threats. 
          Unlike traditional SIEM tools that require constant human monitoring, CyberGuard's 
          agents work 24/7 to analyze logs, identify attack patterns, and generate actionable 
          intelligence.
        </p>
        <div className="p-4 rounded-lg bg-primary/5 border border-primary/20">
          <p className="text-sm text-foreground italic">
            "The interface is designed to mimic a real Security Operations Center dashboard, 
            allowing humans to supervise autonomous AI agents."
          </p>
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {features.map((feature) => (
          <div
            key={feature.title}
            className="p-5 rounded-lg bg-card border border-border hover:border-primary/50 transition-colors"
          >
            <div className="flex items-start gap-4">
              <div className="p-2.5 rounded-lg bg-primary/10">
                <feature.icon className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-1">{feature.title}</h3>
                <p className="text-sm text-muted-foreground">{feature.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Architecture Diagram */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-xl font-semibold text-foreground mb-6">System Architecture</h2>
        
        <div className="space-y-4">
          {/* Data Sources */}
          <div className="p-4 rounded-lg bg-muted/30 border border-border">
            <div className="flex items-center gap-2 mb-3">
              <Layers className="w-5 h-5 text-muted-foreground" />
              <h4 className="font-semibold text-foreground">Data Sources</h4>
            </div>
            <div className="flex flex-wrap gap-2">
              {["Auth Logs", "Network Traffic", "System Events", "Endpoint Data", "Cloud APIs"].map((source) => (
                <span key={source} className="px-3 py-1 rounded-full bg-secondary text-secondary-foreground text-sm">
                  {source}
                </span>
              ))}
            </div>
          </div>

          {/* Arrow */}
          <div className="flex justify-center">
            <GitBranch className="w-6 h-6 text-primary rotate-180" />
          </div>

          {/* Agent Layer */}
          <div className="p-4 rounded-lg bg-primary/5 border border-primary/30">
            <div className="flex items-center gap-2 mb-3">
              <Cpu className="w-5 h-5 text-primary" />
              <h4 className="font-semibold text-foreground">AI Agent Layer</h4>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {["SENTRY", "HUNTER", "DETECTIVE", "JUDGE", "MEDIC", "SCRIBE"].map((agent) => (
                <div key={agent} className="px-3 py-2 rounded bg-primary/10 text-primary text-sm font-mono text-center">
                  {agent}
                </div>
              ))}
            </div>
          </div>

          {/* Arrow */}
          <div className="flex justify-center">
            <GitBranch className="w-6 h-6 text-primary rotate-180" />
          </div>

          {/* Output */}
          <div className="p-4 rounded-lg bg-safe/5 border border-safe/30">
            <div className="flex items-center gap-2 mb-3">
              <Users className="w-5 h-5 text-safe" />
              <h4 className="font-semibold text-foreground">Human Oversight</h4>
            </div>
            <div className="flex flex-wrap gap-2">
              {["Dashboard", "Reports", "Alerts", "Remediation Approval"].map((output) => (
                <span key={output} className="px-3 py-1 rounded-full bg-safe/10 text-safe text-sm border border-safe/30">
                  {output}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Tech Stack */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-xl font-semibold text-foreground mb-4">Technology Stack</h2>
        <div className="flex flex-wrap gap-2">
          {techStack.map((tech) => (
            <div
              key={tech.name}
              className="px-4 py-2 rounded-lg bg-secondary/50 border border-border"
            >
              <p className="font-medium text-foreground">{tech.name}</p>
              <p className="text-xs text-muted-foreground">{tech.category}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Why Agentic AI */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-xl font-semibold text-foreground mb-4">Why Agentic AI?</h2>
        <div className="space-y-4 text-muted-foreground">
          <p>
            Traditional security tools generate thousands of alerts daily, leading to alert 
            fatigue and missed threats. CyberGuard's agentic approach offers several advantages:
          </p>
          <ul className="space-y-2 ml-4">
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span><strong className="text-foreground">Autonomous Triage:</strong> Agents automatically prioritize and investigate alerts</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span><strong className="text-foreground">Contextual Analysis:</strong> Each agent specializes in a specific security domain</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span><strong className="text-foreground">Explainable Decisions:</strong> All agent reasoning is logged and reviewable</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span><strong className="text-foreground">Human-in-the-Loop:</strong> Critical actions require human approval</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center py-8 border-t border-border">
        <p className="text-sm text-muted-foreground">
          CyberGuard • Mini Project 2024 • Autonomous SOC Dashboard
        </p>
      </div>
    </div>
  );
}
