import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { useBackend, type LiveLogRow } from "@/hooks/useBackend";
import { useLiveAlerts, type LiveAlert } from "@/context/LiveAlertsContext";
import {
  getThresholds,
  updateThresholds,
  getAlerts,
  getSmtpStatus,
  postTestEmail,
  getScanHistory,
  postScanPorts,
  getBlockedIPs,
  blockIP,
  unblockIP,
  type BlockedIP,
} from "@/lib/api";
import * as XLSX from 'xlsx';
import { FileSpreadsheet } from "lucide-react";
import { toast } from "sonner";

// ---------- Status colour helpers ----------

const statusColors: Record<string, string> = {
  Failed_Login: "bg-red-500/20 text-red-400 border-red-500/30",
  SQL_Injection: "bg-red-500/20 text-red-400 border-red-500/30",
  Sudo_Escalation: "bg-red-500/20 text-red-400 border-red-500/30",
  Blocked_Connection: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  Port_Scan: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  Rogue_Device: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  DNS_Anomaly: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  Success_Login: "bg-green-500/10 text-green-600 border-green-500/20",
  XSS_Attempt: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  Path_Traversal: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  Command_Injection: "bg-red-600/20 text-red-400 border-red-600/30",
  Dir_Scan: "bg-orange-500/20 text-orange-400 border-orange-500/30",
};

const severityColors: Record<string, string> = {
  CRITICAL: "bg-red-600 text-white",
  HIGH: "bg-orange-600 text-white",
  MEDIUM: "bg-yellow-600 text-black",
  LOW: "bg-blue-600 text-white",
};

function getRowClass(status: string) {
  return statusColors[status] ?? "bg-gray-500/10 text-gray-400 border-gray-500/20";
}

// ---------- Component ----------

export default function ThreatMonitor() {
  const { liveRows, sseConnected } = useBackend();
  const { liveAlerts } = useLiveAlerts();

  // Section state
  const [autoScroll, setAutoScroll] = useState(true);
  const feedRef = useRef<HTMLDivElement>(null);

  // Threshold panel
  const [thresholds, setThresholds] = useState<Record<string, unknown> | null>(null);
  const [showThresholds, setShowThresholds] = useState(false);
  const [thresholdDraft, setThresholdDraft] = useState<Record<string, unknown>>({});

  // Alerts
  const [alertHistory, setAlertHistory] = useState<LiveAlert[]>([]);
  const [alertFilter, setAlertFilter] = useState("ALL");

  // Port scanner
  const [scanResult, setScanResult] = useState<Record<string, unknown> | null>(null);
  const [scanning, setScanning] = useState(false);

  // SMTP
  const [smtpStatus, setSmtpStatus] = useState<{ enabled: boolean; configured: boolean } | null>(null);

  // Blocked IPs
  const [blockedIpList, setBlockedIpList] = useState<BlockedIP[]>([]);
  const [ipToBlock, setIpToBlock] = useState("");

  // ---- Auto-scroll ----
  useEffect(() => {
    if (autoScroll && feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [liveRows, autoScroll]);

  // ---- Load initial data ----
  useEffect(() => {
    getThresholds().then((t) => { setThresholds(t); setThresholdDraft(t); }).catch(() => {});
    getAlerts(200).then((a) => setAlertHistory(a as LiveAlert[])).catch(() => {});
    getScanHistory(1).then((h) => { if ((h as unknown[]).length) setScanResult((h as Record<string, unknown>[])[0]); }).catch(() => {});
    getSmtpStatus().then(setSmtpStatus).catch(() => {});
  }, []);

  const refreshBlockedIPs = useCallback(async () => {
    try {
      const res = await getBlockedIPs();
      setBlockedIpList(res.blocked_ips || []);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    refreshBlockedIPs();
    const int = setInterval(refreshBlockedIPs, 30000);
    return () => clearInterval(int);
  }, [refreshBlockedIPs]);

  // ---- Merge live alerts ----
  useEffect(() => {
    if (liveAlerts.length > 0) {
      setAlertHistory((prev) => {
        const merged = [...prev, ...liveAlerts.filter((a) => !prev.some((p) => p.id === a.id))];
        return merged.slice(-500);
      });
    }
  }, [liveAlerts]);

  // ---- Stats ----
  const recentRows = liveRows.slice(0, 300);
  const oneHourAgo = new Date(Date.now() - 3600_000);
  const recentAlerts = alertHistory.filter((a) => new Date(a.timestamp) > oneHourAgo);
  const blockedIPs = new Set(recentRows.filter((r) => r.status === "Blocked_Connection").map((r) => r.ip_address)).size;
  const failedPerMin = recentRows.filter((r) => r.status === "Failed_Login" && new Date(r.timestamp) > new Date(Date.now() - 60_000)).length;
  const topAttacker = (() => {
    const recent10 = recentRows.filter((r) => new Date(r.timestamp) > new Date(Date.now() - 600_000));
    const counts: Record<string, number> = {};
    recent10.forEach((r) => { counts[r.ip_address] = (counts[r.ip_address] || 0) + 1; });
    return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—";
  })();
  const sqliToday = useMemo(() => {
    const today = new Date().toDateString();
    return liveRows.filter(row =>
      row.status === "SQL_Injection" &&
      new Date(row.timestamp).toDateString() === today
    ).length;
  }, [liveRows]);
  const rogueDevices = recentRows.filter((r) => r.status === "Rogue_Device").length;

  // ---- Handlers ----
  const handleSaveThresholds = useCallback(async () => {
    try {
      const resp = await updateThresholds(thresholdDraft);
      setThresholds((resp as { thresholds: Record<string, unknown> }).thresholds ?? resp);
    } catch { /* ignore */ }
  }, [thresholdDraft]);

  const handleTestEmail = useCallback(async () => {
    try {
      await postTestEmail();
    } catch { /* ignore */ }
  }, []);

  const handleScan = useCallback(async () => {
    setScanning(true);
    try {
      const res = await postScanPorts();
      setScanResult(res);
    } catch { /* ignore */ }
    setScanning(false);
  }, []);

  const handleBlockIP = async () => {
    if (!ipToBlock) return;
    try {
      const res = await blockIP(ipToBlock);
      if (res.status === "blocked") {
        toast.success(`Blocked IP: ${ipToBlock}`);
        setIpToBlock("");
        refreshBlockedIPs();
      } else {
        toast.error(`Error: ${res.message || "Failed to block"}`);
      }
    } catch (e) { toast.error("Failed to block IP"); }
  };

  const handleUnblockIP = async (ip: string) => {
    try {
      const res = await unblockIP(ip);
      if (res.status === "unblocked") {
        toast.success(`Unblocked IP: ${ip}`);
        refreshBlockedIPs();
      } else {
        toast.error(`Error: ${res.message || "Failed to unblock"}`);
      }
    } catch (e) { toast.error("Failed to unblock IP"); }
  };

  const handleExportAlerts = useCallback(() => {
    if (alertHistory.length === 0) {
      toast.error("No alerts to export");
      return;
    }
    const csv = "id,timestamp,severity,ip_address,threshold_name,description\n" +
      alertHistory.map((a) => `${a.id},${a.timestamp},${a.severity},${a.ip_address},${a.threshold_name},"${a.description}"`).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "cyberguard_alerts.csv";
    link.click();
    URL.revokeObjectURL(url);
  }, [alertHistory]);

  const exportToExcel = useCallback(() => {
    if (alertHistory.length === 0) {
      toast.error("No alerts to export");
      return;
    }

    // map alert data to rows
    const rows = alertHistory.map(alert => ({
      Time: alert.timestamp,
      Source: alert.threshold_name,
      'IP Address': alert.ip_address,
      User: "—", // Field not in LiveAlert but requested
      Status: alert.description,
      Endpoint: "—", // Field not in LiveAlert but requested
      Count: alert.current_value,
      Severity: alert.severity
    }));

    // create worksheet
    const worksheet = XLSX.utils.json_to_sheet(rows);

    // set column widths
    worksheet['!cols'] = [
      { wch: 25 }, // Time
      { wch: 20 }, // Source
      { wch: 18 }, // IP Address
      { wch: 12 }, // User
      { wch: 40 }, // Status/Description
      { wch: 15 }, // Endpoint
      { wch: 8  }, // Count
      { wch: 12 }, // Severity
    ];

    // Note: Standard xlsx (community) does not support cell styling and colors.
    // However, the requested properties are added here in case a compatible 
    // styled build is used or if the user intends to switch to Pro/Styled fork.
    
    // Header styling logic (mocked structure)
    const range = XLSX.utils.decode_range(worksheet['!ref'] || 'A1');
    for (let C = range.s.c; C <= range.e.c; ++C) {
      const addr = XLSX.utils.encode_cell({ r: range.s.r, c: C });
      if (!worksheet[addr]) continue;
      worksheet[addr].s = {
        font: { bold: true, color: { rgb: "FFFFFF" } },
        fill: { fgColor: { rgb: "1E3A5F" } },
        alignment: { horizontal: "center" }
      };
    }

    // Row styling logic based on severity
    for (let R = range.s.r + 1; R <= range.e.r; ++R) {
      const severityCell = worksheet[XLSX.utils.encode_cell({ r: R, c: 7 })]; // Severity is col 7
      if (!severityCell) continue;
      
      let color = "";
      if (severityCell.v === "CRITICAL") color = "FEE2E2";
      else if (severityCell.v === "HIGH") color = "FFEDD5";
      else if (severityCell.v === "MEDIUM") color = "FEF9C3";
      else if (severityCell.v === "LOW") color = "DCFCE7";

      if (color) {
        for (let C = range.s.c; C <= range.e.c; ++C) {
          const addr = XLSX.utils.encode_cell({ r: R, c: C });
          if (!worksheet[addr]) continue;
          worksheet[addr].s = { fill: { fgColor: { rgb: color } } };
        }
      }
    }

    // create workbook
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Alert History');

    // download file
    const today = new Date().toISOString().split('T')[0];
    XLSX.writeFile(workbook, `cyberguard_alerts_${today}.xlsx`);
  }, [alertHistory]);

  const filteredAlerts = alertFilter === "ALL" ? alertHistory : alertHistory.filter((a) => a.severity === alertFilter);

  // ---- Threshold fields grouped ----
  const thresholdGroups: Record<string, string[]> = {
    "SSH / Auth": ["failed_login_per_ip_per_minute", "sudo_escalation_per_hour", "new_ssh_key_per_day"],
    "Firewall": ["blocked_connections_per_ip_per_minute", "unique_ports_scanned_per_ip"],
    "Web": ["sqli_attempts_per_ip", "http_4xx_per_ip_per_minute", "http_5xx_per_minute"],
    "Network": ["rogue_device_count", "dns_anomaly_per_hour"],
    "General": ["same_ip_requests_per_minute"],
  };

  return (
    <div className="min-h-screen text-gray-200" style={{ background: "#0d1117", fontFamily: "'JetBrains Mono', monospace" }}>

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 px-3 md:px-6 py-3 border-b" style={{ borderColor: "#30363d", background: "#161b22" }}>
        <div className="flex items-center gap-3">
          <h1 className="text-base md:text-lg font-bold tracking-wide" style={{ color: "#c9d1d9" }}>🛡️ THREAT MONITOR</h1>
          <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full ${sseConnected ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"}`}>
            <span className={`w-2 h-2 rounded-full ${sseConnected ? "bg-green-400 animate-pulse" : "bg-gray-500"}`} />
            {sseConnected ? "LIVE" : "POLLING"}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs" style={{ color: "#8b949e" }}>
          <span>Alerts: <strong className="text-red-400">{recentAlerts.length}</strong></span>
          <span>Events: <strong className="text-blue-400">{liveRows.length}</strong></span>
        </div>
      </div>

      {/* Section 1 — Live Threat Feed */}
      <div className="px-3 md:px-4 pt-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xs md:text-sm font-semibold tracking-wider" style={{ color: "#8b949e" }}>LIVE THREAT FEED</h2>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className="text-xs px-2 py-0.5 rounded border transition-colors"
            style={{ borderColor: "#30363d", background: autoScroll ? "#238636" : "#21262d", color: autoScroll ? "#fff" : "#8b949e" }}
          >
            {autoScroll ? "⏬ Auto-scroll ON" : "⏸ Paused"}
          </button>
        </div>
        <div
          ref={feedRef}
          className="overflow-auto rounded-lg border"
          style={{ maxHeight: "300px", borderColor: "#30363d", background: "#0d1117" }}
        >
          <table className="w-full text-xs" style={{ minWidth: "640px" }}>
            <thead className="sticky top-0" style={{ background: "#161b22" }}>
              <tr className="text-left" style={{ color: "#8b949e" }}>
                <th className="px-3 py-2">Time</th>
                <th className="px-3 py-2">Source</th>
                <th className="px-3 py-2">IP</th>
                <th className="px-3 py-2">User</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Endpoint</th>
                <th className="px-3 py-2">Country</th>
              </tr>
            </thead>
            <tbody>
              {liveRows.slice(0, 200).map((row, i) => (
                <tr
                  key={row.id ?? i}
                  className={`border-b transition-all duration-300 ${getRowClass(row.status)}`}
                  style={{ borderColor: "#21262d", animation: "slideIn 0.3s ease-out" }}
                >
                  <td className="px-3 py-1.5 whitespace-nowrap">{row.timestamp?.split("T")[1]?.slice(0, 8) || row.timestamp}</td>
                  <td className="px-3 py-1.5">{row.source_log ?? "—"}</td>
                  <td className="px-3 py-1.5 font-semibold">{row.ip_address}</td>
                  <td className="px-3 py-1.5">{row.user}</td>
                  <td className="px-3 py-1.5">
                    <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${getRowClass(row.status)}`}>
                      {row.status}
                    </span>
                  </td>
                  <td className="px-3 py-1.5">{row.endpoint}</td>
                  <td className="px-3 py-1.5">{row.country ?? "—"}</td>
                </tr>
              ))}
              {liveRows.length === 0 && (
                <tr><td colSpan={7} className="px-3 py-6 text-center" style={{ color: "#484f58" }}>Waiting for events…</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section 2 — Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 md:gap-3 px-3 md:px-4 pt-4">
        {[
          { label: "Active Alerts", value: recentAlerts.length, color: "#f85149" },
          { label: "Blocked IPs", value: blockedIPs, color: "#e3b341" },
          { label: "Failed /min", value: failedPerMin, color: "#f85149" },
          { label: "Top Attacker", value: topAttacker, color: "#58a6ff" },
          { label: "SQLi Today", value: sqliToday, color: "#f85149" },
          { label: "Rogue Devices", value: rogueDevices, color: "#e3b341" },
        ].map((s) => (
          <div key={s.label} className="rounded-lg border p-3" style={{ borderColor: "#30363d", background: "#161b22" }}>
            <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "#8b949e" }}>{s.label}</div>
            <div className="text-xl font-bold" style={{ color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Bottom row: Threshold Panel + Alerts + Port Scanner */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 px-3 md:px-4 pt-4 pb-8">

        {/* Section 3 — Threshold Config */}
        <div className="rounded-lg border" style={{ borderColor: "#30363d", background: "#161b22" }}>
          <button
            onClick={() => setShowThresholds(!showThresholds)}
            className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold"
            style={{ color: "#c9d1d9" }}
          >
            <span>⚙️ Threshold Configuration</span>
            <span>{showThresholds ? "▲" : "▼"}</span>
          </button>
          {showThresholds && (
            <div className="px-4 pb-4 space-y-4">
              {Object.entries(thresholdGroups).map(([group, keys]) => (
                <div key={group}>
                  <h4 className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: "#58a6ff" }}>{group}</h4>
                  {keys.map((k) => (
                    <div key={k} className="flex items-center gap-2 mb-1">
                      <label className="flex-1 text-xs" style={{ color: "#8b949e" }}>{k.replace(/_/g, " ")}</label>
                      <input
                        type="number"
                        className="w-16 text-xs px-2 py-1 rounded border text-right"
                        style={{ background: "#0d1117", borderColor: "#30363d", color: "#c9d1d9" }}
                        value={String(thresholdDraft[k] ?? thresholds?.[k] ?? "")}
                        onChange={(e) => setThresholdDraft((prev) => ({ ...prev, [k]: Number(e.target.value) }))}
                      />
                    </div>
                  ))}
                </div>
              ))}
              <div className="flex gap-2 pt-2">
                <button
                  onClick={handleSaveThresholds}
                  className="px-3 py-1.5 rounded text-xs font-bold"
                  style={{ background: "#238636", color: "#fff" }}
                >
                  Save Thresholds
                </button>
                <button
                  onClick={handleTestEmail}
                  className="px-3 py-1.5 rounded text-xs font-bold border"
                  style={{ borderColor: "#30363d", color: "#c9d1d9" }}
                >
                  Test Email
                </button>
              </div>
              {smtpStatus && (
                <div className="flex items-center gap-2 text-xs" style={{ color: "#8b949e" }}>
                  <span className={`w-2 h-2 rounded-full ${smtpStatus.configured ? "bg-green-400" : "bg-red-400"}`} />
                  SMTP: {smtpStatus.configured ? "Configured" : "Not configured"}
                </div>
              )}
              <details className="text-xs" style={{ color: "#484f58" }}>
                <summary className="cursor-pointer hover:text-gray-400">Gmail Setup Instructions</summary>
                <ol className="list-decimal list-inside mt-2 space-y-1">
                  <li>Go to https://myaccount.google.com/apppasswords</li>
                  <li>Generate an App Password for "Mail"</li>
                  <li>Set SMTP_PASSWORD=xxxx xxxx xxxx xxxx in backend/.env</li>
                </ol>
              </details>
            </div>
          )}
        </div>

        {/* Section 4 — Alert History Timeline */}
        <div className="rounded-lg border" style={{ borderColor: "#30363d", background: "#161b22" }}>
          <div className="flex items-center justify-between px-4 py-3">
            <h3 className="text-sm font-semibold" style={{ color: "#c9d1d9" }}>🚨 Alert History</h3>
            <div className="flex items-center gap-1">
              {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
                <button
                  key={sev}
                  onClick={() => setAlertFilter(sev)}
                  className={`text-[10px] px-1.5 py-0.5 rounded ${alertFilter === sev ? "font-bold" : ""}`}
                  style={{
                    background: alertFilter === sev ? "#30363d" : "transparent",
                    color: alertFilter === sev ? "#c9d1d9" : "#484f58",
                  }}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>
          <div className="px-4 pb-4 overflow-y-auto" style={{ maxHeight: "300px" }}>
            {filteredAlerts.slice(-50).reverse().map((a) => (
              <div key={a.id} className="flex items-start gap-2 py-2 border-b" style={{ borderColor: "#21262d" }}>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${severityColors[a.severity] ?? ""}`}>
                  {a.severity}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-xs" style={{ color: "#c9d1d9" }}>{a.description}</div>
                  <div className="text-[10px] flex gap-2 mt-0.5" style={{ color: "#484f58" }}>
                    <span>{a.ip_address}</span>
                    <span>{a.timestamp?.split("T")[1]?.slice(0, 8)}</span>
                    {a.auto_blocked && <span className="text-red-400">BLOCKED</span>}
                  </div>
                </div>
              </div>
            ))}
            {filteredAlerts.length === 0 && (
              <p className="text-xs py-4 text-center" style={{ color: "#484f58" }}>No alerts yet</p>
            )}
          </div>
          <div className="px-4 pb-3 flex gap-2">
            <button
              onClick={handleExportAlerts}
              className="text-xs px-2 py-1 rounded border flex items-center gap-1.5 transition-colors hover:bg-white/5"
              style={{ borderColor: "#30363d", color: "#8b949e" }}
            >
              Export CSV
            </button>
            <button
              onClick={exportToExcel}
              className="text-xs px-2 py-1 rounded border flex items-center gap-1.5 transition-all duration-200 hover:brightness-110"
              style={{ background: "#16a34a", borderColor: "#15803d", color: "#fff" }}
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              Export Excel
            </button>
          </div>
        </div>

        {/* Section 5 — Port Exposure */}
        <div className="rounded-lg border" style={{ borderColor: "#30363d", background: "#161b22" }}>
          <div className="flex items-center justify-between px-4 py-3">
            <h3 className="text-sm font-semibold" style={{ color: "#c9d1d9" }}>🔍 Port Exposure</h3>
            <button
              onClick={handleScan}
              disabled={scanning}
              className="text-xs px-2 py-1 rounded font-bold"
              style={{ background: scanning ? "#30363d" : "#238636", color: "#fff" }}
            >
              {scanning ? "Scanning…" : "Scan Now"}
            </button>
          </div>
          <div className="px-4 pb-4">
            {scanResult ? (
              <>
                <div className="text-[10px] mb-2" style={{ color: "#484f58" }}>
                  Last scan: {(scanResult.timestamp as string)?.split("T")[0]} • {scanResult.scan_time as string}
                  {scanResult.mock_data && <span className="ml-2 text-yellow-500">(mock)</span>}
                </div>
                <div className="space-y-1">
                  {((scanResult.open_ports as { port: number; service: string; version: string }[]) ?? []).map((p) => {
                    const allowed = ((scanResult.allowed_ports as number[]) ?? []).includes(p.port);
                    return (
                      <div
                        key={p.port}
                        className="flex items-center gap-2 text-xs px-2 py-1 rounded"
                        style={{ background: allowed ? "#0d1117" : "rgba(248,81,73,0.1)" }}
                      >
                        <span className={`w-2 h-2 rounded-full ${allowed ? "bg-green-400" : "bg-red-400"}`} />
                        <span className="font-bold">{p.port}</span>
                        <span style={{ color: "#8b949e" }}>{p.service}</span>
                        <span style={{ color: "#484f58" }}>{p.version}</span>
                        {!allowed && <span className="ml-auto text-red-400 text-[10px] font-bold">UNEXPECTED</span>}
                      </div>
                    );
                  })}
                </div>
                {((scanResult.unexpected_ports as unknown[]) ?? []).length > 0 && (
                  <p className="text-xs mt-2 text-red-400">
                    ⚠ {(scanResult.unexpected_ports as unknown[]).length} unexpected port(s) detected
                  </p>
                )}
              </>
            ) : (
              <p className="text-xs py-4 text-center" style={{ color: "#484f58" }}>No scan results yet</p>
            )}
          </div>
        </div>
        {/* Section 6 — Blocked IPs */}
        <div className="rounded-lg border" style={{ borderColor: "#30363d", background: "#161b22" }}>
          <div className="flex items-center justify-between px-4 py-3">
            <h3 className="text-sm font-semibold" style={{ color: "#c9d1d9" }}>🚫 Blocked IPs <span className="text-xs text-gray-500 font-normal ml-2">[{blockedIpList.length} blocked]</span></h3>
          </div>
          <div className="px-4 pb-4">
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                placeholder="IP Address..."
                value={ipToBlock}
                onChange={(e) => setIpToBlock(e.target.value)}
                className="flex-1 text-xs px-2 py-1.5 rounded border"
                style={{ background: "#0d1117", borderColor: "#30363d", color: "#c9d1d9" }}
              />
              <button
                onClick={handleBlockIP}
                disabled={!ipToBlock}
                className="text-xs px-3 py-1.5 rounded font-bold disabled:opacity-50"
                style={{ background: "#238636", color: "#fff" }}
              >
                Block
              </button>
            </div>
            
            <div className="space-y-3 overflow-y-auto" style={{ maxHeight: "250px" }}>
              {blockedIpList.length === 0 ? (
                <p className="text-xs text-center" style={{ color: "#484f58" }}>No IPs currently blocked</p>
              ) : (
                blockedIpList.map((b) => (
                  <div key={b.ip} className="p-2 rounded border" style={{ borderColor: "#21262d", background: "#0d1117" }}>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="w-2 h-2 rounded-full bg-red-500" />
                          <span className="font-bold text-red-400 text-sm">{b.ip}</span>
                        </div>
                        <div className="text-[10px]" style={{ color: "#8b949e" }}>
                          Blocked: {b.blocked_at?.split("T").join(" ").slice(0, 19) || "Unknown"}
                        </div>
                        <div className="text-[10px] flex items-center gap-2" style={{ color: "#8b949e" }}>
                          Trigger: {b.trigger}
                          {b.dry_run && <span className="text-[9px] px-1 rounded bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">DRY RUN</span>}
                        </div>
                      </div>
                      <button
                        onClick={() => handleUnblockIP(b.ip)}
                        className="text-[10px] px-2 py-1 rounded border hover:bg-red-500/10 transition-colors"
                        style={{ borderColor: "#f85149", color: "#f85149" }}
                      >
                        Unblock
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
