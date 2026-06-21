import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    Shield,
    ArrowRight,
    Play,
    ChevronRight,
    Zap,
    Brain,
    Lock,
    Activity,
    BarChart3,
    Eye,
    Search,
    Scale,
    Stethoscope,
    PenTool,
    Terminal,
    Database,
    Code2,
    Layers,
    Bot,
    AlertTriangle,
    Globe,
    Cpu,
    Network,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useBackend } from "@/hooks/useBackend";
import { useAuth } from "@/context/AuthContext";
import { LogOut, LayoutDashboard } from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────
interface Agent {
    name: string;
    role: string;
    desc: string;
    icon: React.ElementType;
    color: string;
    border: string;
    bg: string;
    glow: string;
}

interface AttackCard {
    name: string;
    severity: "CRITICAL" | "HIGH" | "MEDIUM";
    icon: React.ElementType;
    desc: string;
    severityColor: string;
}

interface StatItem {
    value: string;
    suffix: string;
    label: string;
    icon: React.ElementType;
    color: string;
}

// ─── Data ─────────────────────────────────────────────────────────────────────
const agents: Agent[] = [
    {
        name: "SENTRY",
        role: "Log Monitor",
        desc: "Scans every log entry for brute force, SQLi & port scanning patterns",
        icon: Eye,
        color: "text-cyan-400",
        border: "border-cyan-500/40",
        bg: "bg-cyan-500/10",
        glow: "shadow-cyan-500/30",
    },
    {
        name: "HUNTER",
        role: "Threat Intel",
        desc: "Cross-checks IPs against AbuseIPDB, VirusTotal & Shodan in real time",
        icon: Search,
        color: "text-orange-400",
        border: "border-orange-500/40",
        bg: "bg-orange-500/10",
        glow: "shadow-orange-500/30",
    },
    {
        name: "DETECTIVE",
        role: "Correlator",
        desc: "Reconstructs the forensic timeline and names the exact attack type",
        icon: Brain,
        color: "text-yellow-400",
        border: "border-yellow-500/40",
        bg: "bg-yellow-500/10",
        glow: "shadow-yellow-500/30",
    },
    {
        name: "JUDGE",
        role: "Risk Scorer",
        desc: "Computes a 0–100 risk score and severity label using weighted rules",
        icon: Scale,
        color: "text-red-400",
        border: "border-red-500/40",
        bg: "bg-red-500/10",
        glow: "shadow-red-500/30",
    },
    {
        name: "MEDIC",
        role: "Responder",
        desc: "Generates iptables firewall commands and account-lockout scripts",
        icon: Stethoscope,
        color: "text-green-400",
        border: "border-green-500/40",
        bg: "bg-green-500/10",
        glow: "shadow-green-500/30",
    },
    {
        name: "SCRIBE",
        role: "Reporter",
        desc: "Authors a CISO-level Markdown incident report with Kill Chain analysis",
        icon: PenTool,
        color: "text-purple-400",
        border: "border-purple-500/40",
        bg: "bg-purple-500/10",
        glow: "shadow-purple-500/30",
    },
];

const attackCards: AttackCard[] = [
    {
        name: "Brute Force",
        severity: "HIGH",
        icon: Lock,
        desc: "Rapid-fire failed login attempts from a single IP",
        severityColor: "text-orange-400 bg-orange-500/15 border-orange-500/40",
    },
    {
        name: "SQL Injection",
        severity: "CRITICAL",
        icon: Database,
        desc: "UNION SELECT, DROP TABLE & malicious query payloads",
        severityColor: "text-red-400 bg-red-500/15 border-red-500/40",
    },
    {
        name: "Port Scanning",
        severity: "MEDIUM",
        icon: Network,
        desc: "Automated probing of /.env, /wp-admin & config files",
        severityColor: "text-yellow-400 bg-yellow-500/15 border-yellow-500/40",
    },
    {
        name: "XSS Attack",
        severity: "HIGH",
        icon: Code2,
        desc: "Script injection via user-controlled input fields",
        severityColor: "text-orange-400 bg-orange-500/15 border-orange-500/40",
    },
    {
        name: "DDoS Attack",
        severity: "CRITICAL",
        icon: Globe,
        desc: "Volumetric traffic flooding targeting application layer",
        severityColor: "text-red-400 bg-red-500/15 border-red-500/40",
    },
    {
        name: "Malware",
        severity: "CRITICAL",
        icon: AlertTriangle,
        desc: "Ransomware, rootkits and fileless attack detection",
        severityColor: "text-red-400 bg-red-500/15 border-red-500/40",
    },
];

const stats: StatItem[] = [
    { value: "99.8", suffix: "%", label: "Detection Accuracy", icon: BarChart3, color: "text-cyan-400" },
    { value: "2.3", suffix: "s", label: "Avg Response Time", icon: Zap, color: "text-purple-400" },
    { value: "6", suffix: "", label: "AI Agents Active", icon: Bot, color: "text-green-400" },
    { value: "50", suffix: "+", label: "Attack Types Covered", icon: Shield, color: "text-orange-400" },
];

const techStack = [
    { name: "React 18", icon: "⚛️", cat: "Frontend" },
    { name: "FastAPI", icon: "⚡", cat: "Backend" },
    { name: "CrewAI", icon: "🤖", cat: "Multi-Agent" },
    { name: "Groq LLaMA 3.3", icon: "🧠", cat: "LLM" },
    { name: "TailwindCSS", icon: "🎨", cat: "Styling" },
    { name: "Shadcn/UI", icon: "🧩", cat: "Components" },
];

// ─── Animated Counter Hook ─────────────────────────────────────────────────────
function useCounter(target: number, duration = 2000, started: boolean) {
    const [count, setCount] = useState(0);
    useEffect(() => {
        if (!started) return;
        let start = 0;
        const step = target / (duration / 16);
        const timer = setInterval(() => {
            start += step;
            if (start >= target) {
                setCount(target);
                clearInterval(timer);
            } else {
                setCount(parseFloat(start.toFixed(1)));
            }
        }, 16);
        return () => clearInterval(timer);
    }, [target, duration, started]);
    return count;
}

// ─── Typewriter Hook ───────────────────────────────────────────────────────────
function useTypewriter(text: string, speed = 60) {
    const [displayed, setDisplayed] = useState("");
    useEffect(() => {
        setDisplayed("");
        let i = 0;
        const timer = setInterval(() => {
            setDisplayed(text.slice(0, i + 1));
            i++;
            if (i >= text.length) clearInterval(timer);
        }, speed);
        return () => clearInterval(timer);
    }, [text, speed]);
    return displayed;
}

// ─── Stat Card Sub-component ───────────────────────────────────────────────────
function StatCounter({ stat, started }: { stat: StatItem; started: boolean }) {
    const num = parseFloat(stat.value);
    const count = useCounter(num, 2000, started);
    return (
        <div className="flex flex-col items-center text-center group">
            <div
                className={cn(
                    "w-14 h-14 rounded-2xl flex items-center justify-center mb-4 border transition-transform duration-300 group-hover:scale-110",
                    "bg-white/5 border-white/10"
                )}
            >
                <stat.icon className={cn("w-6 h-6", stat.color)} />
            </div>
            <div className={cn("text-4xl font-bold font-mono tracking-tight", stat.color)}>
                {count}
                <span className="text-2xl">{stat.suffix}</span>
            </div>
            <div className="text-sm text-slate-400 mt-1 font-medium">{stat.label}</div>
        </div>
    );
}

// ─── Main Home Component ───────────────────────────────────────────────────────
export default function Home() {
    const navigate = useNavigate();
    const { status } = useBackend();
    const [statsVisible, setStatsVisible] = useState(false);
    const [activeAgent, setActiveAgent] = useState(0);
    const statsRef = useRef<HTMLDivElement>(null);
    const videoRef = useRef<HTMLVideoElement>(null);

    const headline = useTypewriter("Cyberguard", 100);
    const { isAuthenticated, logout } = useAuth();

    // Intersection observer for stats counter
    useEffect(() => {
        const observer = new IntersectionObserver(
            ([entry]) => { if (entry.isIntersecting) setStatsVisible(true); },
            { threshold: 0.4 }
        );
        if (statsRef.current) observer.observe(statsRef.current);
        return () => observer.disconnect();
    }, []);

    // Cycle active agent for pipeline animation
    useEffect(() => {
        const id = setInterval(() => {
            setActiveAgent((a) => (a + 1) % agents.length);
        }, 1800);
        return () => clearInterval(id);
    }, []);

    return (
        <div className="min-h-screen bg-[#080b14] text-white overflow-x-hidden">

            {/* ══════════════════════════════════════════════
          HERO — Full-viewport with video background
      ══════════════════════════════════════════════ */}
            <section className="relative min-h-screen flex flex-col items-center justify-center text-center overflow-hidden">

                {/* ── Auth Buttons ── */}
                <div className="absolute top-4 right-4 md:top-6 md:right-8 z-50 flex items-center gap-2 md:gap-3">
                    {!isAuthenticated ? (
                        <>
                            <button
                                onClick={() => navigate("/signin")}
                                className="px-3 md:px-5 py-1.5 md:py-2 rounded-lg border border-cyan-500 text-white text-xs md:text-sm transition-all duration-200 hover:bg-cyan-500 hover:text-[#0d0d1a]"
                            >
                                Sign In
                            </button>
                            <button
                                onClick={() => navigate("/signup")}
                                className="px-3 md:px-5 py-1.5 md:py-2 rounded-lg bg-cyan-500 text-[#0d0d1a] font-semibold text-xs md:text-sm transition-all duration-200 hover:bg-cyan-400"
                            >
                                Sign Up
                            </button>
                        </>
                    ) : (
                        <>
                            <button
                                onClick={() => navigate("/dashboard")}
                                className="px-3 md:px-5 py-1.5 md:py-2 rounded-lg bg-cyan-500 text-[#0d0d1a] font-semibold text-xs md:text-sm transition-all duration-200 hover:bg-cyan-400 flex items-center gap-1.5 md:gap-2"
                            >
                                <LayoutDashboard className="w-3.5 h-3.5 md:w-4 md:h-4" />
                                <span className="hidden sm:inline">Go to </span>Dashboard
                            </button>
                            <button
                                onClick={logout}
                                className="px-3 md:px-5 py-1.5 md:py-2 rounded-lg border border-cyan-500 text-white text-xs md:text-sm transition-all duration-200 hover:bg-cyan-500 hover:text-[#0d0d1a] flex items-center gap-1.5 md:gap-2"
                            >
                                <LogOut className="w-3.5 h-3.5 md:w-4 md:h-4" />
                                <span className="hidden sm:inline">Logout</span>
                            </button>

                        </>
                    )}
                </div>

                {/* Video Background */}
                <video
                    ref={videoRef}
                    autoPlay
                    loop
                    muted
                    playsInline
                    className="absolute inset-0 w-full h-full object-cover opacity-90 contrast-125 brightness-110"
                    aria-hidden="true"
                >
                    <source
                        src="https://assets.mixkit.co/videos/preview/mixkit-abstract-technology-world-map-loop-42352-large.mp4"
                        type="video/mp4"
                    />
                </video>

                {/* Multi-layer gradient overlay — lightened to show video more clearly */}
                <div className="absolute inset-0 bg-gradient-to-b from-[#080b14]/40 via-[#080b14]/10 to-[#080b14] pointer-events-none" />
                <div className="absolute inset-0 bg-gradient-to-r from-blue-900/10 via-transparent to-purple-900/10 pointer-events-none" />


                {/* Animated grid lines */}
                <div
                    className="absolute inset-0 opacity-[0.04] pointer-events-none"
                    style={{
                        backgroundImage:
                            "linear-gradient(rgba(6,182,212,0.8) 1px, transparent 1px), linear-gradient(90deg, rgba(6,182,212,0.8) 1px, transparent 1px)",
                        backgroundSize: "60px 60px",
                    }}
                />

                {/* Glowing orbs */}
                <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] rounded-full bg-blue-600/10 blur-[120px] pointer-events-none" />
                <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full bg-purple-600/10 blur-[100px] pointer-events-none" />

                {/* ── Backend Live Indicator ── */}
                <div className="relative z-10 mb-8 flex items-center gap-2 px-4 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm text-sm font-medium">
                    <span
                        className={cn(
                            "w-2 h-2 rounded-full",
                            status === "idle" ? "bg-green-400 animate-pulse" : "bg-yellow-400 animate-pulse"
                        )}
                    />
                    <span className="text-slate-300">
                        Backend:{" "}
                        <span className={status === "idle" ? "text-green-400" : "text-yellow-400"}>
                            {status === "idle" ? "Live" : "Processing"}
                        </span>
                    </span>
                    <span className="mx-2 text-white/20">|</span>
                    <Bot className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="text-slate-300">6 Agents Ready</span>
                </div>

                {/* ── Main Headline ── */}
                <h1 className="relative z-10 text-5xl sm:text-7xl md:text-9xl font-black tracking-tight leading-none mb-6"
                    aria-label="Cyberguard">
                    <span
                        className="bg-clip-text text-transparent"
                        style={{
                            backgroundImage:
                                "linear-gradient(135deg, #22d3ee 0%, #818cf8 50%, #a78bfa 100%)",
                        }}
                    >
                        {headline}
                        <span className="animate-pulse text-cyan-400">_</span>
                    </span>
                </h1>

                {/* ── Subtitle ── */}
                <p className="relative z-10 text-lg sm:text-xl md:text-2xl text-slate-300 font-light tracking-wide mb-3 max-w-2xl px-4 md:px-6">
                    AI-Powered Autonomous Incident Response
                </p>
                <p className="relative z-10 text-xs md:text-sm text-slate-500 mb-10 max-w-xl px-4 md:px-6">
                    Powered by CrewAI · Groq LLaMA 3.3 · FastAPI · React
                </p>

                {/* ── Feature Badges ── */}
                <div className="relative z-10 flex flex-wrap justify-center gap-3 mb-12 px-6">
                    {[
                        { icon: Cpu, label: "6-Agent Pipeline", color: "text-cyan-400 border-cyan-500/30 bg-cyan-500/10" },
                        { icon: Globe, label: "Live Threat Intel", color: "text-purple-400 border-purple-500/30 bg-purple-500/10" },
                        { icon: Zap, label: "Auto Containment", color: "text-green-400 border-green-500/30 bg-green-500/10" },
                    ].map((badge) => (
                        <div
                            key={badge.label}
                            className={cn(
                                "flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-medium backdrop-blur-sm transition-transform hover:scale-105",
                                badge.color
                            )}
                        >
                            <badge.icon className="w-4 h-4" />
                            {badge.label}
                        </div>
                    ))}
                </div>

                {/* ── CTAs ── */}
                <div className="relative z-10 flex flex-col sm:flex-row gap-4 items-center px-6">
                    <button
                        onClick={() => navigate(isAuthenticated ? "/dashboard" : "/signin")}
                        className="group flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-base text-black transition-all duration-300 hover:scale-105 hover:shadow-[0_0_40px_rgba(34,211,238,0.4)]"
                        style={{ background: "linear-gradient(135deg, #22d3ee, #818cf8)" }}
                    >
                        Launch Dashboard
                        <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
                    </button>
                    <button
                        onClick={() => navigate("/investigation")}
                        className="flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-base border border-white/20 bg-white/5 backdrop-blur-sm text-white transition-all duration-300 hover:bg-white/10 hover:border-white/30 hover:scale-105"
                    >
                        <Play className="w-4 h-4" />
                        View Agent Pipeline
                    </button>
                </div>

                {/* ── Scroll Indicator ── */}
                <div className="relative z-10 absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 opacity-50">
                    <span className="text-xs text-slate-500 tracking-widest uppercase">Scroll</span>
                    <div className="w-5 h-8 rounded-full border border-slate-600 flex items-start justify-center pt-1.5">
                        <div className="w-1 h-2 bg-slate-400 rounded-full animate-bounce" />
                    </div>
                </div>
            </section>

            {/* ══════════════════════════════════════════════
          SECTION 2 — Agent Pipeline
      ══════════════════════════════════════════════ */}
            <section className="relative py-24 px-6">
                <div className="max-w-7xl mx-auto">
                    {/* Section Header */}
                    <div className="text-center mb-16">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 text-xs font-semibold uppercase tracking-widest mb-4">
                            <Activity className="w-3 h-3" />
                            Multi-Agent Pipeline
                        </div>
                        <h2 className="text-4xl md:text-5xl font-bold mb-4 text-white">
                            Six Agents.{" "}
                            <span className="bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(135deg, #22d3ee, #a78bfa)" }}>
                                One Mission.
                            </span>
                        </h2>
                        <p className="text-slate-400 text-lg max-w-xl mx-auto">
                            Each agent is a specialist. Together, they form an autonomous SOC that never sleeps.
                        </p>
                    </div>

                    {/* Pipeline Flow — Desktop */}
                    <div className="hidden lg:flex items-stretch justify-between gap-2 mb-16">
                        {agents.map((agent, idx) => (
                            <div key={agent.name} className="flex items-center gap-2 flex-1">
                                <div
                                    className={cn(
                                        "flex-1 p-5 rounded-2xl border-2 transition-all duration-500 cursor-default",
                                        agent.bg,
                                        agent.border,
                                        activeAgent === idx
                                            ? `shadow-lg ${agent.glow} scale-105`
                                            : "opacity-70 hover:opacity-100 hover:scale-102"
                                    )}
                                >
                                    <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center mb-3", agent.bg, "border", agent.border)}>
                                        <agent.icon className={cn("w-5 h-5", agent.color)} />
                                    </div>
                                    <p className={cn("text-xs font-black tracking-widest mb-0.5 font-mono", agent.color)}>
                                        {agent.name}
                                    </p>
                                    <p className="text-white text-sm font-semibold mb-2">{agent.role}</p>
                                    <p className="text-slate-400 text-xs leading-relaxed">{agent.desc}</p>
                                    {activeAgent === idx && (
                                        <div className={cn("mt-3 flex items-center gap-1.5 text-xs font-medium", agent.color)}>
                                            <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                                            Active
                                        </div>
                                    )}
                                </div>
                                {idx < agents.length - 1 && (
                                    <ChevronRight className="w-5 h-5 text-slate-600 flex-shrink-0" />
                                )}
                            </div>
                        ))}
                    </div>

                    {/* Pipeline Flow — Mobile/Tablet Grid */}
                    <div className="grid lg:hidden grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 mb-12">
                        {agents.map((agent, idx) => (
                            <div
                                key={agent.name}
                                className={cn(
                                    "p-5 rounded-2xl border-2 transition-all duration-500",
                                    agent.bg,
                                    agent.border,
                                    activeAgent === idx ? `shadow-lg ${agent.glow}` : "opacity-80"
                                )}
                            >
                                <div className="flex items-center gap-3 mb-3">
                                    <div className={cn("w-9 h-9 rounded-lg flex items-center justify-center", agent.bg, "border", agent.border)}>
                                        <agent.icon className={cn("w-4 h-4", agent.color)} />
                                    </div>
                                    <div>
                                        <p className={cn("text-xs font-black font-mono tracking-widest", agent.color)}>{agent.name}</p>
                                        <p className="text-white text-sm font-semibold">{agent.role}</p>
                                    </div>
                                </div>
                                <p className="text-slate-400 text-xs leading-relaxed">{agent.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ══════════════════════════════════════════════
          SECTION 3 — Animated Stats
      ══════════════════════════════════════════════ */}
            <section ref={statsRef} className="relative py-24 px-6 border-y border-white/5">
                {/* Gradient background */}
                <div className="absolute inset-0 bg-gradient-to-r from-blue-950/30 via-purple-950/20 to-blue-950/30 pointer-events-none" />

                <div className="relative max-w-5xl mx-auto">
                    <div className="text-center mb-16">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-purple-500/30 bg-purple-500/10 text-purple-400 text-xs font-semibold uppercase tracking-widest mb-4">
                            <Zap className="w-3 h-3" />
                            By the Numbers
                        </div>
                        <h2 className="text-4xl md:text-5xl font-bold text-white">
                            Enterprise-Grade{" "}
                            <span className="bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(135deg, #a78bfa, #22d3ee)" }}>
                                Performance
                            </span>
                        </h2>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
                        {stats.map((stat) => (
                            <StatCounter key={stat.label} stat={stat} started={statsVisible} />
                        ))}
                    </div>
                </div>
            </section>

            {/* ══════════════════════════════════════════════
          SECTION 4 — Attack Types Grid
      ══════════════════════════════════════════════ */}
            <section className="py-24 px-6">
                <div className="max-w-6xl mx-auto">
                    <div className="text-center mb-16">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-red-500/30 bg-red-500/10 text-red-400 text-xs font-semibold uppercase tracking-widest mb-4">
                            <AlertTriangle className="w-3 h-3" />
                            Threat Detection Coverage
                        </div>
                        <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
                            Every Attack.{" "}
                            <span className="bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(135deg, #fb923c, #f87171)" }}>
                                Detected.
                            </span>
                        </h2>
                        <p className="text-slate-400 text-lg max-w-xl mx-auto">
                            From classic brute-force to sophisticated multi-vector intrusions — Cyberguard has you covered.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                        {attackCards.map((attack) => (
                            <div
                                key={attack.name}
                                className="group relative p-6 rounded-2xl border border-white/8 bg-white/[0.02] hover:bg-white/[0.05] transition-all duration-300 hover:border-white/20 hover:shadow-lg hover:-translate-y-1 overflow-hidden"
                            >
                                {/* Subtle gradient on hover */}
                                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-br from-white/5 to-transparent pointer-events-none rounded-2xl" />

                                <div className="flex items-start justify-between mb-4">
                                    <div className="w-11 h-11 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
                                        <attack.icon className="w-5 h-5 text-slate-300" />
                                    </div>
                                    <span
                                        className={cn(
                                            "text-xs font-bold px-2.5 py-1 rounded-full border font-mono tracking-wider",
                                            attack.severityColor
                                        )}
                                    >
                                        {attack.severity}
                                    </span>
                                </div>
                                <h3 className="text-white font-bold text-lg mb-2">{attack.name}</h3>
                                <p className="text-slate-400 text-sm leading-relaxed">{attack.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ══════════════════════════════════════════════
          SECTION 5 — How It Works
      ══════════════════════════════════════════════ */}
            <section className="py-24 px-6 border-t border-white/5">
                <div className="max-w-5xl mx-auto">
                    <div className="text-center mb-16">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-green-500/30 bg-green-500/10 text-green-400 text-xs font-semibold uppercase tracking-widest mb-4">
                            <Terminal className="w-3 h-3" />
                            Workflow
                        </div>
                        <h2 className="text-4xl md:text-5xl font-bold text-white">
                            How It{" "}
                            <span className="bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(135deg, #4ade80, #22d3ee)" }}>
                                Works
                            </span>
                        </h2>
                    </div>

                    <div className="grid md:grid-cols-2 gap-6">
                        {[
                            {
                                num: "01",
                                title: "Ingest Logs",
                                desc: "Upload your CSV auth/network logs via the dashboard, or let the built-in simulator generate a realistic multi-vector attack dataset.",
                                icon: Database,
                                color: "text-cyan-400 border-cyan-500/30 bg-cyan-500/10",
                            },
                            {
                                num: "02",
                                title: "Agent Analysis",
                                desc: "SENTRY scans for patterns → HUNTER verifies IPs against AbuseIPDB, Shodan & VirusTotal → DETECTIVE reconstructs the forensic timeline.",
                                icon: Brain,
                                color: "text-purple-400 border-purple-500/30 bg-purple-500/10",
                            },
                            {
                                num: "03",
                                title: "Risk Scoring",
                                desc: "JUDGE computes a weighted 0–100 Risk Score: SQL Injection +50, Brute Force +30, Scanning +10, coordinated attack bonus +20.",
                                icon: BarChart3,
                                color: "text-orange-400 border-orange-500/30 bg-orange-500/10",
                            },
                            {
                                num: "04",
                                title: "Response & Report",
                                desc: "MEDIC generates iptables firewall commands. SCRIBE authors a full CISO-level Markdown incident report with Kill Chain breakdown.",
                                icon: Shield,
                                color: "text-green-400 border-green-500/30 bg-green-500/10",
                            },
                        ].map((step) => (
                            <div
                                key={step.num}
                                className="flex gap-5 p-6 rounded-2xl border border-white/8 bg-white/[0.02] hover:bg-white/[0.04] transition-all duration-300 group"
                            >
                                <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 border transition-transform group-hover:scale-110 duration-300", step.color)}>
                                    <step.icon className="w-5 h-5" />
                                </div>
                                <div>
                                    <div className="text-xs font-mono text-slate-600 mb-1">{step.num}</div>
                                    <h3 className="text-white font-bold text-lg mb-2">{step.title}</h3>
                                    <p className="text-slate-400 text-sm leading-relaxed">{step.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ══════════════════════════════════════════════
          SECTION 6 — Tech Stack
      ══════════════════════════════════════════════ */}
            <section className="py-24 px-6 border-t border-white/5">
                <div className="max-w-4xl mx-auto text-center">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-slate-500/30 bg-slate-500/10 text-slate-400 text-xs font-semibold uppercase tracking-widest mb-4">
                        <Layers className="w-3 h-3" />
                        Built With
                    </div>
                    <h2 className="text-4xl font-bold text-white mb-12">
                        Production-Grade{" "}
                        <span className="bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(135deg, #94a3b8, #e2e8f0)" }}>
                            Stack
                        </span>
                    </h2>

                    <div className="flex flex-wrap justify-center gap-4">
                        {techStack.map((tech) => (
                            <div
                                key={tech.name}
                                className="flex items-center gap-3 px-5 py-3 rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.07] hover:border-white/20 transition-all duration-200 hover:scale-105 cursor-default"
                            >
                                <span className="text-xl">{tech.icon}</span>
                                <div className="text-left">
                                    <p className="text-white font-semibold text-sm">{tech.name}</p>
                                    <p className="text-slate-500 text-xs">{tech.cat}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ══════════════════════════════════════════════
          CTA BANNER
      ══════════════════════════════════════════════ */}
            <section className="py-24 px-6">
                <div
                    className="max-w-4xl mx-auto rounded-3xl p-6 md:p-12 text-center relative overflow-hidden"
                    style={{
                        background: "linear-gradient(135deg, rgba(34,211,238,0.1) 0%, rgba(129,140,248,0.1) 50%, rgba(167,139,250,0.1) 100%)",
                        border: "1px solid rgba(129,140,248,0.2)",
                    }}
                >
                    {/* Glow */}
                    <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-purple-500/5 to-transparent pointer-events-none" />

                    <div
                        className="inline-flex w-20 h-20 rounded-2xl items-center justify-center mb-6 mx-auto"
                        style={{ background: "linear-gradient(135deg, rgba(34,211,238,0.2), rgba(167,139,250,0.2))", border: "1px solid rgba(129,140,248,0.3)" }}
                    >
                        <Shield className="w-10 h-10 text-purple-400" />
                    </div>

                    <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-4">
                        Ready to Secure Your{" "}
                        <span className="bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(135deg, #22d3ee, #a78bfa)" }}>
                            Infrastructure?
                        </span>
                    </h2>
                    <p className="text-slate-400 text-lg mb-10 max-w-lg mx-auto">
                        Launch the dashboard and run your first AI-powered security investigation in seconds.
                    </p>

                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <button
                            onClick={() => navigate(isAuthenticated ? "/dashboard" : "/signin")}

                            className="group flex items-center justify-center gap-2 px-10 py-4 rounded-xl font-bold text-base text-black transition-all duration-300 hover:scale-105 hover:shadow-[0_0_50px_rgba(34,211,238,0.35)]"
                            style={{ background: "linear-gradient(135deg, #22d3ee, #818cf8)" }}
                        >
                            Launch Dashboard
                            <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
                        </button>
                        <button
                            onClick={() => navigate("/report")}
                            className="flex items-center justify-center gap-2 px-10 py-4 rounded-xl font-bold text-base border border-white/20 bg-white/5 text-white transition-all duration-300 hover:bg-white/10 hover:scale-105"
                        >
                            View Sample Report
                        </button>
                    </div>
                </div>
            </section>

            {/* ══════════════════════════════════════════════
          FOOTER
      ══════════════════════════════════════════════ */}
            <footer className="border-t border-white/5 py-10 px-6">
                <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-slate-500">
                    <div className="flex items-center gap-2">
                        <Shield className="w-4 h-4 text-cyan-500" />
                        <span className="font-semibold text-slate-300">Cyberguard</span>
                        <span>· Autonomous SOC Platform</span>
                    </div>

                    <div className="flex items-center gap-6">
                        <a
                            href="https://github.com"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-white transition-colors flex items-center gap-1.5"
                            aria-label="GitHub"
                        >
                            <Code2 className="w-4 h-4" />
                            GitHub
                        </a>
                        <button onClick={() => navigate("/about")} className="hover:text-white transition-colors">
                            Architecture
                        </button>
                        <button onClick={() => navigate("/dashboard")} className="hover:text-white transition-colors">
                            Dashboard
                        </button>
                    </div>

                    <p>
                        Built with{" "}
                        <span className="text-red-400">❤️</span>{" "}
                        · © {new Date().getFullYear()} Cyberguard
                    </p>
                </div>
            </footer>
        </div>
    );
}
