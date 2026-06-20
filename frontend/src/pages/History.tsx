import { useEffect, useState } from "react";
import { getIncidents, type Incident } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  Shield,
  AlertTriangle,
  Clock,
  Globe,
  Filter,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  FileText,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { deleteIncident } from "@/lib/api";

const severityColors: Record<string, string> = {
  CRITICAL: "bg-red-500/15 text-red-400 border-red-500/40",
  HIGH: "bg-orange-500/15 text-orange-400 border-orange-500/40",
  MEDIUM: "bg-yellow-500/15 text-yellow-400 border-yellow-500/40",
  LOW: "bg-green-500/15 text-green-400 border-green-500/40",
};

const statusColors: Record<string, string> = {
  open: "bg-cyan-500/15 text-cyan-400 border-cyan-500/40",
  closed: "bg-gray-500/15 text-gray-400 border-gray-500/40",
  investigating: "bg-purple-500/15 text-purple-400 border-purple-500/40",
};

export default function History() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [attackFilter, setAttackFilter] = useState<string>("ALL");

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log("Fetching incidents from API...");
      const data = await getIncidents();
      console.log("Incidents received:", data);
      setIncidents(data || []);
    } catch (err: any) {
      console.error("Error fetching incidents:", err);
      setError(err.message || "Failed to load incidents");
      toast.error("Failed to load incidents");
      setIncidents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDelete = async (incidentId: string) => {
    if (!confirm(`Delete incident ${incidentId}?`)) return;
    try {
      await deleteIncident(incidentId);
      toast.success(`Incident ${incidentId} deleted`);
      setIncidents((prev) => prev.filter((i) => i.incident_id !== incidentId));
    } catch (err: any) {
      toast.error("Failed to delete incident");
    }
  };

  // Get unique attack types for filter
  const attackTypes = [
    "ALL",
    ...Array.from(new Set(incidents.map((i) => i.attack_type).filter(Boolean) as string[])),
  ];

  const filtered = incidents.filter((inc) => {
    if (severityFilter !== "ALL" && inc.severity !== severityFilter) return false;
    if (attackFilter !== "ALL" && inc.attack_type !== attackFilter) return false;
    return true;
  });

  return (
    <div className="space-y-4 md:space-y-6 p-3 md:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-white flex items-center gap-3">
            <div className="w-9 h-9 md:w-10 md:h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
              <FileText className="w-4 h-4 md:w-5 md:h-5 text-cyan-400" />
            </div>
            Incident History
          </h1>
          <p className="text-slate-400 text-sm mt-1 ml-12 md:ml-[52px]">
            {incidents.length} total incident{incidents.length !== 1 ? "s" : ""} recorded
          </p>
        </div>
        <Button
          onClick={fetchData}
          variant="outline"
          size="sm"
          className="border-white/10 bg-white/5 text-white hover:bg-white/10"
        >
          <RefreshCw className={cn("w-4 h-4 mr-2", loading && "animate-spin")} />
          Refresh
        </Button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap gap-2 md:gap-3 p-3 md:p-4 rounded-xl border border-white/10 bg-white/[0.02]">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Filter className="w-4 h-4" />
          <span className="hidden sm:inline">Filters:</span>
        </div>
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="bg-gray-900 border border-gray-700 text-white text-sm rounded-lg px-3 py-1.5 focus:ring-cyan-500 focus:border-cyan-500"
        >
          <option value="ALL">All Severities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
        <select
          value={attackFilter}
          onChange={(e) => setAttackFilter(e.target.value)}
          className="bg-gray-900 border border-gray-700 text-white text-sm rounded-lg px-3 py-1.5 focus:ring-cyan-500 focus:border-cyan-500"
        >
          {attackTypes.map((t) => (
            <option key={t} value={t}>
              {t === "ALL" ? "All Attack Types" : t}
            </option>
          ))}
        </select>
        <span className="text-xs text-slate-500 self-center ml-auto">
          Showing {filtered.length} of {incidents.length}
        </span>
      </div>

      {/* Incident Cards */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin" />
          <span className="ml-3 text-slate-400">Loading incidents...</span>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center mb-4">
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>
          <h3 className="text-white font-semibold text-lg mb-2">Failed to Load History</h3>
          <p className="text-slate-500 text-sm max-w-sm mb-4">
            There was a problem fetching incidents from the server.
            <br />
            {error}
          </p>
          <Button onClick={fetchData} variant="outline" className="border-red-500/30 text-red-400 hover:bg-red-500/10">
            <RefreshCw className="w-4 h-4 mr-2" />
            Try Again
          </Button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
            <Shield className="w-8 h-8 text-slate-500" />
          </div>
          <h3 className="text-white font-semibold text-lg mb-2">No incidents found</h3>
          <p className="text-slate-500 text-sm max-w-sm">
            {incidents.length === 0
              ? "Run a simulation from the Dashboard to generate your first incident report. Or, check your active filters."
              : "No incidents match the current filters. Try adjusting your filter criteria."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((inc) => {
            const isExpanded = expandedId === inc.incident_id;
            return (
              <div
                key={inc.id}
                className="rounded-xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.04] transition-all duration-200 overflow-hidden"
              >
                {/* Card Header */}
                <div
                  className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 p-4 md:p-5 cursor-pointer"
                  onClick={() => setExpandedId(isExpanded ? null : inc.incident_id)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className="text-cyan-400 font-mono font-bold text-sm">
                        {inc.incident_id}
                      </span>
                      {inc.severity && (
                        <span
                          className={cn(
                            "text-xs font-bold px-2 py-0.5 rounded-full border font-mono",
                            severityColors[inc.severity] || severityColors.MEDIUM
                          )}
                        >
                          {inc.severity}
                        </span>
                      )}
                      <span
                        className={cn(
                          "text-xs px-2 py-0.5 rounded-full border",
                          statusColors[inc.status] || statusColors.open
                        )}
                      >
                        {inc.status}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 md:gap-4 text-sm text-slate-400">
                      {inc.attack_type && (
                        <span className="flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-orange-400" />
                          {inc.attack_type}
                        </span>
                      )}
                      {inc.source_ip && (
                        <span className="flex items-center gap-1.5">
                          <Globe className="w-3.5 h-3.5 text-purple-400" />
                          {inc.source_ip}
                        </span>
                      )}
                      <span className="flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5" />
                        {new Date(inc.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {inc.risk_score != null && (
                      <div className="text-right">
                        <div
                          className={cn(
                            "text-2xl font-bold font-mono",
                            (inc.risk_score ?? 0) >= 80
                              ? "text-red-400"
                              : (inc.risk_score ?? 0) >= 50
                              ? "text-orange-400"
                              : "text-green-400"
                          )}
                        >
                          {inc.risk_score}
                        </div>
                        <div className="text-xs text-slate-500">Risk Score</div>
                      </div>
                    )}
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-slate-500" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-slate-500" />
                    )}
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="px-5 pb-5 pt-0 border-t border-white/5">
                    <div className="pt-4 space-y-3">
                      {inc.agent_notes && inc.agent_notes.length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                            Agent Notes
                          </h4>
                          <div className="space-y-1.5">
                            {inc.agent_notes.map((note, i) => (
                              <div
                                key={i}
                                className="text-sm text-slate-300 font-mono bg-black/30 px-3 py-2 rounded-lg"
                              >
                                {note}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      <div className="flex justify-end pt-2">
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(inc.incident_id);
                          }}
                          className="bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20"
                        >
                          <Trash2 className="w-4 h-4 mr-1.5" />
                          Delete
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
