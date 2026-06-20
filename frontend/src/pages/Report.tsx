import { useEffect, useState } from "react";
import { FileText, Download, Shield } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { fetchReportRaw, fetchStructuredReport, type StructuredReport } from "@/lib/api";

/* ─── Severity colour helpers ─── */
const severityColor = (s?: string | null) => {
  switch (s?.toUpperCase()) {
    case "CRITICAL": return { bg: "#7f1d1d", fg: "#fca5a5", border: "#ef4444" };
    case "HIGH":     return { bg: "#78350f", fg: "#fcd34d", border: "#f59e0b" };
    case "MEDIUM":   return { bg: "#713f12", fg: "#fde68a", border: "#eab308" };
    case "LOW":      return { bg: "#064e3b", fg: "#6ee7b7", border: "#10b981" };
    default:         return { bg: "#1f2937", fg: "#9ca3af", border: "#4b5563" };
  }
};

const riskColor = (score: number) => {
  if (score >= 80) return "#ef4444";
  if (score >= 50) return "#f59e0b";
  if (score >= 30) return "#eab308";
  return "#10b981";
};

/* ─── Custom markdown component map ─── */
const markdownComponents = {
  h1: ({ children, ...props }: any) => (
    <h1
      style={{
        fontSize: "1.5rem",
        fontWeight: 700,
        color: "#06b6d4",
        borderBottom: "2px solid rgba(6,182,212,0.35)",
        paddingBottom: "0.5rem",
        marginTop: "2rem",
        marginBottom: "1rem",
        letterSpacing: "-0.01em",
      }}
      {...props}
    >
      {children}
    </h1>
  ),
  h2: ({ children, ...props }: any) => (
    <h2
      style={{
        fontSize: "1.25rem",
        fontWeight: 600,
        color: "#a78bfa",
        marginTop: "1.75rem",
        marginBottom: "0.75rem",
      }}
      {...props}
    >
      {children}
    </h2>
  ),
  h3: ({ children, ...props }: any) => (
    <h3
      style={{
        fontSize: "1.05rem",
        fontWeight: 600,
        color: "#34d399",
        marginTop: "1.25rem",
        marginBottom: "0.5rem",
      }}
      {...props}
    >
      {children}
    </h3>
  ),
  h4: ({ children, ...props }: any) => (
    <h4
      style={{
        fontSize: "0.95rem",
        fontWeight: 600,
        color: "#93c5fd",
        marginTop: "1rem",
        marginBottom: "0.4rem",
      }}
      {...props}
    >
      {children}
    </h4>
  ),
  p: ({ children, ...props }: any) => (
    <p
      style={{
        color: "#d1d5db",
        lineHeight: 1.8,
        marginBottom: "1rem",
        fontSize: "0.95rem",
      }}
      {...props}
    >
      {children}
    </p>
  ),
  ul: ({ children, ...props }: any) => (
    <ul
      style={{ marginBottom: "1rem", paddingLeft: "1.25rem" }}
      {...props}
    >
      {children}
    </ul>
  ),
  ol: ({ children, ...props }: any) => (
    <ol
      style={{ marginBottom: "1rem", paddingLeft: "1.25rem" }}
      {...props}
    >
      {children}
    </ol>
  ),
  li: ({ children, ...props }: any) => (
    <li
      style={{
        color: "#d1d5db",
        lineHeight: 1.8,
        marginBottom: "0.35rem",
        fontSize: "0.95rem",
      }}
      {...props}
    >
      {children}
    </li>
  ),
  strong: ({ children, ...props }: any) => (
    <strong style={{ color: "#f9fafb", fontWeight: 600 }} {...props}>
      {children}
    </strong>
  ),
  em: ({ children, ...props }: any) => (
    <em style={{ color: "#c4b5fd", fontStyle: "italic" }} {...props}>
      {children}
    </em>
  ),
  code: ({ children, className, ...props }: any) => {
    // If inside a <pre>, render as block code
    const isInline = !className;
    if (isInline) {
      return (
        <code
          style={{
            background: "#1e293b",
            color: "#34d399",
            padding: "0.15rem 0.45rem",
            borderRadius: "4px",
            fontSize: "0.85rem",
            fontFamily: "'JetBrains Mono', monospace",
          }}
          {...props}
        >
          {children}
        </code>
      );
    }
    return (
      <code
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: "0.85rem",
        }}
        className={className}
        {...props}
      >
        {children}
      </code>
    );
  },
  pre: ({ children, ...props }: any) => (
    <pre
      style={{
        background: "#0f172a",
        border: "1px solid #1e293b",
        borderRadius: "8px",
        padding: "1rem 1.25rem",
        overflowX: "auto",
        marginBottom: "1rem",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: "0.85rem",
        color: "#34d399",
        lineHeight: 1.6,
      }}
      {...props}
    >
      {children}
    </pre>
  ),
  blockquote: ({ children, ...props }: any) => (
    <blockquote
      style={{
        borderLeft: "4px solid #06b6d4",
        paddingLeft: "1rem",
        margin: "1rem 0",
        color: "#9ca3af",
        fontStyle: "italic",
      }}
      {...props}
    >
      {children}
    </blockquote>
  ),
  hr: (props: any) => (
    <hr
      style={{
        border: "none",
        borderTop: "1px solid #1f2937",
        margin: "2rem 0",
      }}
      {...props}
    />
  ),
  table: ({ children, ...props }: any) => (
    <div style={{ overflowX: "auto", marginBottom: "1rem" }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: "0.9rem",
        }}
        {...props}
      >
        {children}
      </table>
    </div>
  ),
  th: ({ children, ...props }: any) => (
    <th
      style={{
        background: "#1e293b",
        color: "#93c5fd",
        padding: "0.6rem 1rem",
        textAlign: "left",
        borderBottom: "2px solid #334155",
        fontSize: "0.85rem",
        fontWeight: 600,
      }}
      {...props}
    >
      {children}
    </th>
  ),
  td: ({ children, ...props }: any) => (
    <td
      style={{
        padding: "0.5rem 1rem",
        borderBottom: "1px solid #1e293b",
        color: "#d1d5db",
      }}
      {...props}
    >
      {children}
    </td>
  ),
};

/* ─── Report page ─── */
export default function Report() {
  const [markdown, setMarkdown] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [structured, setStructured] = useState<StructuredReport | null>(null);

  useEffect(() => {
    let mounted = true;
    console.log("=== Report page: fetching data ===");
    Promise.all([
      fetchReportRaw().catch((e) => {
        console.error("=== Report page: fetchReportRaw error:", e);
        if (mounted) setError(e instanceof Error ? e.message : String(e));
        return "";
      }),
      fetchStructuredReport().catch((e) => {
        console.error("=== Report page: fetchStructuredReport error:", e);
        return null;
      }),
    ])
      .then(([raw, s]) => {
        if (!mounted) return;
        console.log("=== Report page: raw length:", raw?.length, "structured:", !!s);
        setMarkdown(raw || "");
        if (s) setStructured(s);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handlePDFExport = () => {
    window.print();
  };

  const sev = severityColor(structured?.severity);
  const riskNum = parseInt(String(structured?.risk_score || "0"), 10) || 0;

  return (
    <div className="p-3 md:p-6 max-w-5xl mx-auto space-y-4 md:space-y-6 report-page">
      {/* ── Page header ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            style={{
              background: "linear-gradient(135deg, #06b6d4, #3b82f6)",
              borderRadius: "10px",
              padding: "0.55rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <FileText className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">Incident Report</h1>
            <p style={{ color: "#6b7280", fontSize: "0.8rem", marginTop: "1px" }}>
              AI-generated forensic analysis
            </p>
          </div>
        </div>
        {markdown && markdown.length > 0 && (
          <button
            onClick={handlePDFExport}
            className="no-print"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              background: "linear-gradient(135deg, #1e293b, #0f172a)",
              border: "1px solid #334155",
              color: "#93c5fd",
              padding: "0.5rem 1.1rem",
              borderRadius: "8px",
              fontSize: "0.85rem",
              fontWeight: 500,
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "#06b6d4";
              e.currentTarget.style.color = "#06b6d4";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "#334155";
              e.currentTarget.style.color = "#93c5fd";
            }}
          >
            <Download className="w-4 h-4" />
            Export PDF
          </button>
        )}
      </div>

      {/* ── Structured header card ── */}
      {structured && (
        <div
          className="no-print-hide"
          style={{
            background: "linear-gradient(135deg, #0c1929 0%, #111827 50%, #0f172a 100%)",
            border: "1px solid #1e293b",
            borderRadius: "12px",
            overflow: "hidden",
          }}
        >
          {/* Top banner */}
          <div
            style={{
              background: "linear-gradient(135deg, #1e3a5f, #1a1f35)",
              borderBottom: "1px solid #1e3a5f",
              padding: "1.25rem 1.75rem",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <Shield className="w-5 h-5" style={{ color: "#3b82f6" }} />
              <div>
                <p style={{ color: "#64748b", fontSize: "0.7rem", letterSpacing: "0.08em", textTransform: "uppercase", margin: 0 }}>
                  Cyberguard Incident Report
                </p>
                <p style={{ color: "#f1f5f9", fontSize: "1.05rem", fontWeight: 600, margin: 0, marginTop: "2px", fontFamily: "'JetBrains Mono', monospace" }}>
                  {structured.incident_id || "INC-UNKNOWN"}
                </p>
              </div>
            </div>
            <span
              style={{
                background: sev.bg,
                color: sev.fg,
                padding: "0.35rem 1.1rem",
                borderRadius: "20px",
                fontSize: "0.8rem",
                fontWeight: 600,
                border: `1px solid ${sev.border}`,
                letterSpacing: "0.04em",
              }}
            >
              {structured.severity || "UNKNOWN"}
            </span>
          </div>

          {/* Metrics row */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
              gap: "1px",
              background: "#1e293b",
            }}
          >
            {/* Risk Score */}
            <div style={{ background: "#111827", padding: "1.1rem 1.5rem" }}>
              <div style={{ color: "#64748b", fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.35rem" }}>
                Risk Score
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: "0.3rem" }}>
                <span style={{ fontSize: "1.6rem", fontWeight: 700, color: riskColor(riskNum), fontFamily: "'JetBrains Mono', monospace" }}>
                  {riskNum}
                </span>
                <span style={{ fontSize: "0.85rem", color: "#64748b" }}>/100</span>
              </div>
              {/* Mini progress bar */}
              <div style={{ marginTop: "0.5rem", background: "#1e293b", borderRadius: "4px", height: "4px", overflow: "hidden" }}>
                <div
                  style={{
                    width: `${riskNum}%`,
                    height: "100%",
                    background: `linear-gradient(90deg, ${riskColor(riskNum)}, ${riskColor(riskNum)}cc)`,
                    borderRadius: "4px",
                    transition: "width 1s ease",
                  }}
                />
              </div>
            </div>

            {/* Attack Type */}
            <div style={{ background: "#111827", padding: "1.1rem 1.5rem" }}>
              <div style={{ color: "#64748b", fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.35rem" }}>
                Attack Type
              </div>
              <div style={{ color: "#f1f5f9", fontSize: "0.9rem", fontWeight: 500 }}>
                {structured.attack_type || "-"}
              </div>
            </div>

            {/* Source IP */}
            <div style={{ background: "#111827", padding: "1.1rem 1.5rem" }}>
              <div style={{ color: "#64748b", fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.35rem" }}>
                Source IP
              </div>
              <div
                style={{
                  color: "#f87171",
                  fontSize: "0.9rem",
                  fontWeight: 500,
                  fontFamily: "'JetBrains Mono', monospace",
                }}
              >
                {structured.source_ip || "-"}
              </div>
            </div>

            {/* Service */}
            <div style={{ background: "#111827", padding: "1.1rem 1.5rem" }}>
              <div style={{ color: "#64748b", fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.35rem" }}>
                Targeted Service
              </div>
              <div style={{ color: "#f1f5f9", fontSize: "0.9rem", fontWeight: 500 }}>
                {structured.targeted_service || "-"}
              </div>
            </div>
          </div>

          {/* Recommended actions (collapsible row) */}
          {structured.recommended_actions?.length ? (
            <div style={{ borderTop: "1px solid #1e293b", padding: "1rem 1.5rem" }}>
              <div style={{ color: "#64748b", fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
                Recommended Actions
              </div>
              <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
                {structured.recommended_actions.map((a, i) => (
                  <li key={i} style={{ color: "#d1d5db", fontSize: "0.88rem", lineHeight: 1.7 }}>
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}

      {/* ── Report body ── */}
      <div
        className="report-container"
        style={{
          background: "#111827",
          border: "1px solid #1e293b",
          borderRadius: "12px",
          padding: "clamp(1rem, 4vw, 2.5rem)",
          fontFamily: "'Inter', sans-serif",
        }}
      >
        {loading ? (
          <div style={{ textAlign: "center", padding: "3rem 0" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                border: "3px solid #1e293b",
                borderTopColor: "#06b6d4",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
                margin: "0 auto 1rem",
              }}
            />
            <p style={{ color: "#6b7280", fontSize: "0.9rem" }}>Loading report…</p>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </div>
        ) : error ? (
          <div
            style={{
              background: "#1c1917",
              border: "1px solid #7f1d1d",
              borderRadius: "8px",
              padding: "1rem 1.25rem",
              color: "#fca5a5",
              fontSize: "0.9rem",
            }}
          >
            ⚠️ {error}
          </div>
        ) : markdown && markdown.length > 0 ? (
          <>
            <ReactMarkdown components={markdownComponents}>{markdown}</ReactMarkdown>
            {/* Footer */}
            <div
              style={{
                marginTop: "3rem",
                paddingTop: "1rem",
                borderTop: "1px solid #1e293b",
                display: "flex",
                justifyContent: "space-between",
                color: "#4b5563",
                fontSize: "0.75rem",
                flexWrap: "wrap",
                gap: "0.5rem",
              }}
            >
              <span>Generated by Cyberguard AI SOC Platform</span>
              <span>Powered by CrewAI + Groq LLaMA 3.3</span>
            </div>
          </>
        ) : (
          <div style={{ textAlign: "center", padding: "3rem 0" }}>
            <FileText className="w-10 h-10 mx-auto" style={{ color: "#334155", marginBottom: "1rem" }} />
            <p style={{ color: "#6b7280", fontSize: "0.95rem", marginBottom: "0.25rem" }}>
              No report content available yet
            </p>
            <p style={{ color: "#4b5563", fontSize: "0.8rem" }}>
              Upload a CSV and run a simulation to generate a forensic report.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
