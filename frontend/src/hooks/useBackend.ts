import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { AgentLog } from "@/components/dashboard/AgentFeed";
import { fetchLogs, fetchStatus, runSimulation, resetSession, getStreamUrl, getAgentFeedUrl, fetchAgentMessages } from "@/lib/api";

export interface LiveLogRow {
  timestamp: string;
  ip_address: string;
  user: string;
  status: string;
  endpoint: string;
  source_log?: string;
  raw_line?: string;
  country?: string;
  city?: string;
  id?: number;
}

// Module-level persistence — survives component unmount/remount
let _persistedLiveRows: LiveLogRow[] = [];

export function useBackend() {
  const [status, setStatus] = useState<"running" | "idle" | "complete">("idle");
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [agentLogs, setAgentLogs] = useState<AgentLog[]>([]);
  const [liveRows, setLiveRows] = useState<LiveLogRow[]>(_persistedLiveRows);
  const [sseConnected, setSseConnected] = useState(false);
  const [agentFeedConnected, setAgentFeedConnected] = useState(false);
  const logIdCounter = useRef(0);
  const agentLogIdCounter = useRef(0);
  const usingSSE = useRef(false);

  // SSE connection for logs (Live Monitor - /stream)
  useEffect(() => {
    let es: EventSource | null = null;
    let fallbackId: ReturnType<typeof setInterval> | null = null;

    function connectSSE() {
      try {
        es = new EventSource(getStreamUrl());

        es.onopen = () => {
          setSseConnected(true);
          usingSSE.current = true;
          if (fallbackId) {
            clearInterval(fallbackId);
            fallbackId = null;
          }
        };

        es.onmessage = (event) => {
          try {
            console.log("=== SSE /stream event received:", event.data.substring(0, 120));
            const parsed = JSON.parse(event.data);
            if (parsed.type === "log" && parsed.data) {
              const row = parsed.data as LiveLogRow;
              const id = `sse-log-${logIdCounter.current++}`;
              const newLog: AgentLog = {
                id,
                agent: "SYSTEM",
                message: `${row.timestamp} | ${row.ip_address} | ${row.user} | ${row.status} | ${row.endpoint}`,
                timestamp: new Date(),
                type: row.status?.includes("Failed") || row.status?.includes("SQL") ? "warning" : "info",
              };
              setLogs((prev) => [...prev.slice(-500), newLog]);
              setLiveRows((prev) => {
                const updated = [row, ...prev].slice(0, 2000);
                _persistedLiveRows = updated;
                return updated;
              });
            }
          } catch {
            // ignore parse errors
          }
        };

        es.onerror = () => {
          setSseConnected(false);
          usingSSE.current = false;
          es?.close();
          es = null;
          startPolling();
        };
      } catch {
        startPolling();
      }
    }

    function startPolling() {
      if (fallbackId) return;
      fallbackId = setInterval(async () => {
        try {
          const l = await fetchLogs();
          const lines = l.split(/\r?\n/).filter((x) => x.trim().length > 0);
          const content = lines.slice(1);
          const mapped: AgentLog[] = content.map((line, i) => ({
            id: `backend-log-${i}`,
            agent: "SYSTEM",
            message: line,
            timestamp: new Date(),
            type: "info",
          }));
          setLogs(mapped);
        } catch {
          // ignore
        }
      }, 10000);
    }

    connectSSE();

    return () => {
      es?.close();
      if (fallbackId) clearInterval(fallbackId);
    };
  }, []);

  // SSE connection for Agent Feed (Dashboard - /agent-feed)
  useEffect(() => {
    let agentEs: EventSource | null = null;

    function connectAgentFeed() {
      try {
        agentEs = new EventSource(getAgentFeedUrl());

        agentEs.onopen = () => {
          setAgentFeedConnected(true);
        };

        agentEs.addEventListener("agent", (event) => {
          try {
            const msg = JSON.parse((event as MessageEvent).data);
            const id = `agent-${agentLogIdCounter.current++}`;
            const newLog: AgentLog = {
              id,
              agent: msg.agent || "SYSTEM",
              message: msg.message || "",
              timestamp: new Date(msg.timestamp || Date.now()),
              type: msg.type || "info",
            };
            setAgentLogs((prev) => [...prev.slice(-200), newLog]);
          } catch {
            // ignore parse errors
          }
        });

        agentEs.onerror = () => {
          setAgentFeedConnected(false);
          agentEs?.close();
          agentEs = null;
          // Retry after 5 seconds
          setTimeout(connectAgentFeed, 5000);
        };
      } catch {
        setTimeout(connectAgentFeed, 5000);
      }
    }

    connectAgentFeed();

    return () => {
      agentEs?.close();
    };
  }, []);

  // Poll status every 3 seconds (unchanged)
  useEffect(() => {
    const poll = async () => {
      try {
        const s = await fetchStatus();
        console.log('session_active from backend:', s.session_active);
        setStatus(s.status);
      } catch {
        // ignore
      }
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);


  // If not using SSE, also fetch initial logs
  useEffect(() => {
    if (usingSSE.current) return;
    fetchLogs()
      .then((l) => {
        const lines = l.split(/\r?\n/).filter((x) => x.trim().length > 0);
        console.log('fetchLogs called — logs returned:', lines.length - 1);
        const content = lines.slice(1);
        const mapped: AgentLog[] = content.map((line, i) => ({
          id: `backend-log-${i}`,
          agent: "SYSTEM",
          message: line,
          timestamp: new Date(),
          type: "info",
        }));
        setLogs(mapped);
      })
      .catch(() => {});
  }, []);


  const start = useCallback(async () => {
    // Clear restored agent logs before starting new investigation
    setAgentLogs([]);
    agentLogIdCounter.current = 0;
    await runSimulation();
    setStatus("running");
  }, []);

  // Restore agent messages from last investigation on mount
  useEffect(() => {
    fetchAgentMessages()
      .then((data) => {
        if (data.messages && data.messages.length > 0 && agentLogIdCounter.current === 0) {
          const restored: AgentLog[] = data.messages.map((msg, i) => ({
            id: `restored-${i}`,
            agent: msg.agent || "SYSTEM",
            message: msg.message || "",
            timestamp: new Date(msg.timestamp || Date.now()),
            type: (msg.type || "info") as AgentLog["type"],
          }));
          setAgentLogs(restored);
          agentLogIdCounter.current = restored.length;
        }
      })
      .catch(() => {});
  }, []);

  const reset = useCallback(async () => {
    try {
      await resetSession();
    } catch (err) {
      console.error("Failed to reset session on backend:", err);
    }
    setLogs([]);
    setAgentLogs([]);
    _persistedLiveRows = [];
    setLiveRows([]);
    setStatus("idle");
  }, []);

  const statusBadge = useMemo(() => status, [status]);

  return { status: statusBadge, logs, agentLogs, liveRows, start, reset, sseConnected, agentFeedConnected };
}
