# CodeRazz — Agent Engineering Rules and Protocols (AGENTS.md)

This document defines the strict engineering guidelines, architecture contracts, and operational protocols for any AI agent or software engineer contributing to **CodeRazz: A Misconception-Aware Programming Tutor**.

---

## 1. Project Vision & Identity

- **Project Name:** CodeRazz
- **Tagline:** *Don't just fix the code. Understand the thinking behind it.*
- **Core Mission:** Traditional online judges stop at reporting *Wrong Answer (WA)*, *Runtime Error (RE)*, or *Time Limit Exceeded (TLE)*. CodeRazz identifies the **underlying programming misconception** causing the failure, provides structured, progressive hints (without revealing solutions), and arms teachers with actionable class-wide diagnostic insights.

---

## 2. Strict ₹0 Budget & Zero-Paid-Tools Policy

1. **Zero External Billing:**
   - Under no circumstances shall paid APIs (OpenAI, Anthropic, Google Cloud paid APIs, AWS paid services) be introduced as required runtime dependencies.
   - Core runtime dependencies must be 100% free and open-source (FOSS).
2. **Local-First & Offline Resilience:**
   - Code execution: Local isolated Docker containers.
   - Database: Local PostgreSQL via Docker Compose (with SQLite development fallback if Docker daemon is stopped).
   - Misconception classification: Scikit-learn, AST analysis, heuristic pattern rules, and test-case probe signatures.
   - Hint generation: Validated misconception-specific semantic templates with optional local Ollama LLM enhancement when configured.
3. **No Secret Leaks:**
   - Never commit API keys, database passwords, or secret credentials to Git. Always use `.env.example` templates and load from environment variables.

---

## 3. Engineering Team Personas & Responsibilities

When developing CodeRazz, work with the rigor of a full engineering team:

| Persona | Primary Focus & Quality Standards |
|---|---|
| **Software Architect** | System modularity, clean domain-driven separation, robust API contracts, and adherence to design principles. |
| **Python Backend Engineer** | High-performance FastAPI endpoints, SQLAlchemy 2 async/sync best practices, Alembic migrations, and Pydantic validation. |
| **Frontend/UI Engineer** | Accessible, responsive, aesthetic Next.js App Router (Node.js 22 LTS standard), Tailwind CSS, Monaco Editor integration, Recharts analytics, and zero-jank UX. |
| **AI/ML Engineer** | Authoritative 30-class taxonomy mapping (A1-G3 + S1/S2), AST traversal, probe test design, modular Scikit-learn feature engineering, and empirical calibration. |
| **DevSecOps Engineer** | Container sandboxing (non-root, network severed, read-only root, dropped capabilities, no-new-privileges, pids-limit, zero secrets/socket mounts), and host isolation. |
| **QA Engineer** | Comprehensive Pytest unit and integration suites, Vitest frontend tests, E2E validation, and negative security test cases. |

---

## 4. Architectural Principles & Boundaries

1. **Separation of Concerns:**
   - `frontend/`: Next.js 15+ App Router, React 19, TypeScript, Tailwind CSS, shadcn/ui components, Monaco Editor. Standardized on Node.js 22 LTS.
   - `backend/`: FastAPI application, authentication (JWT + bcrypt), API routing, database ORM models, business logic.
   - `execution/`: Sandboxed code execution service with isolated Docker runners and safe fallback execution wrappers.
   - `ml/`: Hybrid misconception detection engine (AST analyzer, rule engine, diagnostic probe runner, Scikit-learn classifier, calibration).
   - `dataset/`: Ground truth taxonomy definitions (30 core classes + 2 meta-classes), synthetic & curated benchmark programs, and evaluation matrices.
   - `docs/`: Living documentation: `ARCHITECTURE.md`, `IMPLEMENTATION_PLAN.md`, `DECISIONS.md`, `TESTING.md`.

2. **Untrusted Code Protocol & Sandbox Boundaries:**
   - **Student code is strictly untrusted.** Never execute student code within the primary FastAPI application process or bare host.
   - Host subprocess fallback is **strictly restricted to trusted local development smoke tests**. It does not constitute a secure sandbox.
   - Docker container execution must enforce: non-root user (`uid=10001:10001`), read-only root filesystem, `--network none`, dropped Linux capabilities (`--cap-drop=ALL`), `--security-opt=no-new-privileges`, hard CPU quota (1 core max), memory ceiling (128 MB max), process ceiling (`--pids-limit 32`), wall-clock timeout (3.0s max), and restricted stdout/stderr capture (64 KB max).
   - Under no circumstances shall application secrets, environment files, or the host Docker socket (`docker.sock`) be mounted into execution containers.
   - Public deployment requires kernel-isolated virtualization (gVisor or Firecracker).

3. **Database Protocol:**
   - **PostgreSQL 16** is the primary, production target database.
   - **SQLite** is permitted solely as a development convenience for offline bootstrapping when Docker daemon is stopped.
   - All migrations and database behaviors must be validated against PostgreSQL.

4. **ML Reliability & Confidence Heuristics:**
   - Treat diagnostic confidence thresholds (e.g. 0.70 / 0.40) as configurable experimental parameters, not proven facts.
   - Deterministic AST rules and diagnostic probes take precedence. ML classification is modular and must be calibrated on labelled data.

5. **Hint Ladder & Solution-Leak Protection:**
   - CodeRazz must never give away complete code solutions to students.
   - Every generated or retrieved hint must pass through the `SolutionLeakGuard` before being transmitted to the client.
   - The 5 hint tiers must be preserved:
     - **Level 1: Nudge** (directional question highlighting behavior).
     - **Level 2: Conceptual Explanation** (clarifies the underlying computing principle).
     - **Level 3: Counter-Example** (specific minimal input where the code fails).
     - **Level 4: Worked Analogue** (isomorphic problem example demonstrating correct pattern).
     - **Level 5: Targeted Pointer** (identifies the specific faulty construct without handing over code).

6. **Data Integrity & Ground Truth:**
   - Never fabricate benchmark results, evaluation metrics, or student logs.
   - Always clearly label synthetic test datasets versus validated empirical cases.

---

## 5. Development Workflow & Change Discipline

- **Inspect First:** Check file contents and workspace state before editing.
- **Incremental Steps:** Implement features in isolated, testable steps adhering to the phase roadmap.
- **Verify with Tests:** Run automated tests to prove functionality before declaring a task complete.
- **Maintain Docs:** Keep `IMPLEMENTATION_PLAN.md`, `ARCHITECTURE.md`, `DECISIONS.md`, and `TESTING.md` up to date with every major milestone.
- **Safety First:** Obtain confirmation before running destructive operations (e.g., dropping database tables, deleting repository directories).
