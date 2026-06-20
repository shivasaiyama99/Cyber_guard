import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: "up" | "down" | "neutral";
  severity?: "critical" | "high" | "medium" | "safe" | "default";
  subtitle?: string;
}

export function StatCard({
  title,
  value,
  icon: Icon,
  severity = "default",
  subtitle,
}: StatCardProps) {
  const severityStyles = {
    critical: "border-critical/50 bg-critical/5",
    high: "border-high/50 bg-high/5",
    medium: "border-medium/50 bg-medium/5",
    safe: "border-safe/50 bg-safe/5",
    default: "border-border bg-card",
  };

  const iconStyles = {
    critical: "text-critical bg-critical/10",
    high: "text-high bg-high/10",
    medium: "text-medium bg-medium/10",
    safe: "text-safe bg-safe/10",
    default: "text-primary bg-primary/10",
  };

  const valueStyles = {
    critical: "text-critical",
    high: "text-high",
    medium: "text-medium",
    safe: "text-safe",
    default: "text-foreground",
  };

  return (
    <div
      className={cn(
        "relative p-3 md:p-5 rounded-lg border transition-all duration-300 card-glow",
        severityStyles[severity],
        severity === "critical" && "pulse-critical"
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
            {title}
          </p>
          <p
            className={cn(
              "text-2xl md:text-3xl font-bold tracking-tight",
              valueStyles[severity]
            )}
          >
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
          )}
        </div>
        <div className={cn("p-2.5 rounded-lg", iconStyles[severity])}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}
