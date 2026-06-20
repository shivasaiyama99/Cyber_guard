# Technology Stack

**Analysis Date:** 2025-02-05

## Languages

**Primary:**
- Python 3.10+ - Backend logic, agent execution, API server.
- TypeScript 5.8+ - Frontend application logic and UI components.

**Secondary:**
- JavaScript (ESM) - Build configurations and scripts.
- YAML - CrewAI agent and task definitions (`backend/src/cyberguard/config/`).

## Runtime

**Environment:**
- Python 3.10 to 3.13 (Managed by `uv`).
- Node.js 18+ (Frontend development and build).

**Package Manager:**
- `uv` - Backend dependencies (`backend/pyproject.toml`, `backend/uv.lock`).
- `npm` - Frontend dependencies (`frontend/package.json`, `frontend/package-lock.json`).

## Frameworks

**Core:**
- FastAPI 0.128+ - Backend REST API server (`backend/server.py`).
- CrewAI 1.9.3 - Multi-agent orchestration framework (`backend/src/cyberguard/crew.py`).
- React 18.3 - Frontend UI framework (`frontend/src/`).
- Vite 5.4 - Frontend build tool and dev server (`frontend/vite.config.ts`).

**Testing:**
- Vitest 3.2 - Frontend unit and integration testing (`frontend/package.json`).
- Testing Library (React) - Frontend component testing.

**Build/Dev:**
- Tailwind CSS 3.4 - Utility-first CSS framework (`frontend/tailwind.config.ts`).
- PostCSS 8.5 - CSS transformation.
- Shadcn UI - Accessible UI component library (based on Radix UI).

## Key Dependencies

**Critical:**
- `crewai` 1.9.3 - Powers the core agentic AI logic.
- `langchain-groq` 1.1.2 - LLM interface for Groq models.
- `litellm` 1.75.3 - Universal LLM interface used by CrewAI.
- `fastapi` - High-performance web framework for the API.
- `@tanstack/react-query` 5.83 - Frontend data fetching and state management.

**Infrastructure:**
- `apscheduler` - Task scheduling (though simulation is triggered manually/via background tasks).
- `pandas` - Data manipulation for log scanning (`backend/src/cyberguard/tools/security_tools.py`).
- `lucide-react` - Icon library for the frontend.
- `recharts` - Charting library for the dashboard.

## Configuration

**Environment:**
- Backend: `.env` file for API keys and log levels.
- Frontend: `import.meta.env` (Vite) for `VITE_API_BASE_URL`.

**Build:**
- `backend/pyproject.toml` - Python project config.
- `frontend/vite.config.ts` - Vite build config.
- `frontend/tsconfig.json` - TypeScript compiler options.
- `frontend/tailwind.config.ts` - Tailwind theme and plugin config.

## Platform Requirements

**Development:**
- Python 3.10+
- Node.js 18+
- API keys for LLM providers (Groq) and threat intelligence (AbuseIPDB, VirusTotal).

**Production:**
- Python runtime for backend.
- Static file hosting for frontend (built via Vite).

---

*Stack analysis: 2025-02-05*
