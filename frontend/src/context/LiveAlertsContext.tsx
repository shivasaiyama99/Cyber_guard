import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { getAlertsLiveUrl } from "@/lib/api";

export interface LiveAlert {
  id: string;
  timestamp: string;
  threshold_name: string;
  current_value: number;
  threshold_value: number;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  ip_address: string;
  description: string;
  auto_blocked: boolean;
}

interface LiveAlertsContextValue {
  liveAlerts: LiveAlert[];
  clearAlerts: () => void;
}

const LiveAlertsContext = createContext<LiveAlertsContextValue | null>(null);

export function LiveAlertsProvider({ children }: { children: ReactNode }) {
  const [liveAlerts, setLiveAlerts] = useState<LiveAlert[]>([]);
  const connectionRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function connectAlerts() {
      // Prevent duplicate connections
      if (connectionRef.current) {
        return;
      }

      try {
        const es = new EventSource(getAlertsLiveUrl());
        connectionRef.current = es;

        es.addEventListener("alert", (event) => {
          try {
            const alert = JSON.parse((event as MessageEvent).data) as LiveAlert;
            setLiveAlerts((prev) => [...prev.slice(-499), alert]);
          } catch {
            // ignore parse errors
          }
        });

        es.onerror = () => {
          es.close();
          connectionRef.current = null;
          // Retry after 5 seconds
          reconnectTimeoutRef.current = setTimeout(connectAlerts, 5000);
        };
      } catch {
        reconnectTimeoutRef.current = setTimeout(connectAlerts, 5000);
      }
    }

    connectAlerts();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (connectionRef.current) {
        connectionRef.current.close();
        connectionRef.current = null;
      }
    };
  }, []);

  const clearAlerts = () => setLiveAlerts([]);

  return (
    <LiveAlertsContext.Provider value={{ liveAlerts, clearAlerts }}>
      {children}
    </LiveAlertsContext.Provider>
  );
}

export function useLiveAlerts(): LiveAlertsContextValue {
  const ctx = useContext(LiveAlertsContext);
  if (!ctx) {
    throw new Error("useLiveAlerts must be used within LiveAlertsProvider");
  }
  return ctx;
}
