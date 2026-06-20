import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

export interface AgentLog {
  id: string;
  agent: string;
  message: string;
  timestamp: Date;
  type: "info" | "warning" | "success" | "error";
}

interface AgentFeedProps {
  logs: AgentLog[];
}

// Agent badge colors: SENTRY=blue, HUNTER=red, DETECTIVE=yellow, JUDGE=orange, MEDIC=green, SCRIBE=purple
const agentBadgeColors: Record<string, string> = {
  SENTRY: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  HUNTER: "bg-red-500/20 text-red-400 border-red-500/30",
  DETECTIVE: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  JUDGE: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  MEDIC: "bg-green-500/20 text-green-400 border-green-500/30",
  SCRIBE: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  SYSTEM: "bg-gray-500/20 text-gray-400 border-gray-500/30",
};

const typeIndicator: Record<string, string> = {
  info: "bg-primary/50",
  warning: "bg-high/50",
  success: "bg-safe/50",
  error: "bg-critical/50",
};

export function AgentFeed({ logs }: AgentFeedProps) {
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTo({
        top: feedRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [logs]);


  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-critical/70" />
            <div className="w-3 h-3 rounded-full bg-medium/70" />
            <div className="w-3 h-3 rounded-full bg-safe/70" />
          </div>
          <span className="text-sm font-medium text-muted-foreground ml-2">
            Live Agent Feed
          </span>
        </div>
        <span className="text-xs text-muted-foreground font-mono">
          {logs.length} entries
        </span>
      </div>

      {/* Terminal Content */}
      <div
        ref={feedRef}
        className="flex-1 p-4 overflow-y-auto terminal-scroll bg-background/50 relative scanlines"
      >
        {logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground text-sm gap-2">
            <span className="animate-pulse">Waiting for investigation...</span>
            <span className="text-xs text-muted-foreground/70">
              Upload a CSV and start an investigation to see agent activity
            </span>
          </div>
        ) : (
          <div className="space-y-1 font-mono text-sm">
            {logs.map((log, index) => (
              <div
                key={log.id}
                className={cn(
                  "flex items-start gap-2 py-1 animate-fade-in",
                  index === logs.length - 1 && "bg-primary/5 -mx-2 px-2 rounded"
                )}
              >
                <div
                  className={cn(
                    "w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0",
                    typeIndicator[log.type]
                  )}
                />
                <span className="text-muted-foreground text-xs flex-shrink-0">
                  {log.timestamp.toLocaleTimeString("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: false,
                  })}
                </span>
                <span
                  className={cn(
                    "text-xs font-semibold flex-shrink-0 px-1.5 py-0.5 rounded border",
                    agentBadgeColors[log.agent] || agentBadgeColors.SYSTEM
                  )}
                >
                  {log.agent}
                </span>
                <span className="text-foreground/90 break-all">{log.message}</span>
              </div>
            ))}
            <div className="flex items-center gap-1 text-primary pt-2">

              <span className="animate-pulse">▌</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
