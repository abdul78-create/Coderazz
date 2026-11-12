# CodeRazz — Architectural Decision Records (ADRs)

This document records the architectural and technology decisions made for CodeRazz, capturing the context, alternatives considered, decision rationale, and trade-offs.

---

## ADR-001: ₹0 Budget & Zero-Paid-Tools Strategy

### Context
CodeRazz must be accessible, reproducible, and verifiable without requiring ongoing paid API credits (OpenAI, Anthropic, Gemini paid tiers, AWS paid services, or proprietary database hosting). The project must operate sustainably on zero budget.

### Decision
- Core misconception detection, classification, test execution, and hint generation will rely entirely on **free, open-source technologies**.
- Machine learning will use **Scikit-learn**, Python `ast`, and diagnostic test probing.
- Hint generation will use **curated, high-fidelity misconception templates** by default, with an optional adapter for **local Ollama instances** (e.g., Llama 3 / Mistral / DeepSeek-Coder running on the user's hardware) without external cloud costs.
- Database: Local **PostgreSQL 16** run via Docker Compose, with an automated SQLite development mode when Docker is offline.

### Consequences
- **Pros:** Zero operational expense, no credit card requirements, reproducible anywhere, complete data privacy for student submissions.
- **Cons:** Advanced generative re-phrasing requires local GPU/RAM if Ollama is enabled; template quality must be rigorously crafted.

---

## ADR-002: Sandboxed Code Execution & Fallback Boundary Clarification

### Context
Student code execution poses major security risks: fork bombs, infinite loops, memory bloat, disk exhaustion, network abuse, and local file tampering. We need an execution sandbox that is strictly secure yet feasible for local developers whose Docker daemon might not be running immediately.

### Decision
1. **Primary Sandbox:** Disposable Linux Docker containers with:
   - `--network none` (zero network egress/ingress)
   - `--read-only` root filesystem
   - `--tmpfs /tmp:rw,noexec,nosuid,size=16m`
   - `--user 10001:10001` (unprivileged execution)
   - `--cap-drop=ALL` (drops all Linux capabilities)
   - `--security-opt=no-new-privileges`
   - `--pids-limit 32` (blocks fork-bombs and runaway thread spawning)
   - `--cpus 1.0` and `--memory 128m`
   - Wall-clock timeout of 3.0 seconds max via container stop/kill
   - **Zero Secret Mounting:** No host application paths, `.env` files, database passwords, or Docker socket (`docker.sock`) are mounted into execution containers.
2. **Host Subprocess Fallback Boundary Warning:**
   - AST screening and process limits **do NOT make arbitrary code execution safe** on the host.
   - The host subprocess runner is **strictly restricted to trusted local development smoke tests**.
   - Untrusted student submissions must **never** be executed via the host subprocess runner or within the main FastAPI application process.
3. **Public Deployment Roadmap:**
   - Before accepting public internet submissions, execution sandboxing must be bolstered with kernel-isolated virtualization (such as gVisor `runsc` or Firecracker microVMs).

### Consequences
- **Pros:** Robust defense-in-depth in production; zero credential exposure; unprivileged non-root execution.
- **Cons:** Docker Desktop daemon must be active to test untrusted code submissions safely.

---

## ADR-003: Hybrid Misconception Engine (Rules + AST + Probes + Modular ML)

### Context
A pure machine learning model (e.g. LLM or deep neural network) suffers from hallucinations, non-deterministic outputs, and lack of explainability. A pure rule-based system is brittle and fails on novel syntax variations.

### Decision
We implement a **hybrid diagnostic pipeline**:
1. **AST & Syntax Heuristic Matchers:** High-precision deterministic checks for canonical beginner misconceptions (e.g., assignment in condition, uninitialized accumulator, misplaced return in loop).
2. **Diagnostic Test Probes:** Specialized test inputs (edge cases, empty lists, single element) to probe specific failure behaviors.
3. **Scikit-learn Classifier (Modular):** Extracts token n-grams and AST node frequency vectors, classifying into the 30-class taxonomy.
4. **Evidence Synthesizer:** Pairs the predicted misconception with line numbers, code snippets, and human-readable pedagogical explanations.
5. **Configurable Confidence Thresholds:** Initial thresholds ($\ge 0.70$ for high confidence, $< 0.40$ for low confidence) are **starting heuristic assumptions**, not empirically calibrated ground truth. They must be validated and calibrated against annotated student data before being treated as production probabilities.
6. **Rule-First Priority:** Deterministic AST and probe rules take priority initially. ML classification is modular and introduced progressively as validated benchmark data is collected.

### Consequences
- **Pros:** High explainability, fast execution (< 50ms), pedagogical rigor, graceful degradation.
- **Cons:** Requires initial curation of probe inputs and AST visitor routines.

---

## ADR-004: Five-Tier Progressive Hint Ladder with SolutionLeakGuard

### Context
Educational research demonstrates that giving students direct code fixes short-circuits cognitive learning. Conversely, vague error messages cause frustration and dropout.

### Decision
Implement a rigid 5-level hint progression:
- `Level 1: Nudge` — Highlights where the issue manifests.
- `Level 2: Conceptual Explanation` — Explains the computer science principle.
- `Level 3: Counter-Example` — Demonstrates a minimal failing input.
- `Level 4: Worked Analogue` — Demonstrates a parallel problem and pattern.
- `Level 5: Targeted Pointer` — Pinpoints the exact line and construct.

All hints (whether template-based or local-LLM-augmented) must pass through `SolutionLeakGuard`, which checks:
- AST subtree similarity against the canonical solution.
- N-gram token overlap thresholds.
- Regular expressions for variable reassignments and return expressions matching the reference code.

### Consequences
- **Pros:** Safe scaffolding that preserves pedagogical integrity and academic honesty.
- **Cons:** Students cannot skip directly to Level 5 unless allowed by assignment configuration.

---

## ADR-005: Technology Stack Selection & Node.js 22 LTS Standardization

### Context
We require a modern, responsive, high-performance web frontend and a robust backend using stable long-term-supported runtimes.

### Decision
- **Node Runtime:** Standardize on **Node.js 22 LTS** for predictable, long-term stability and modern toolchain compatibility.
- **Frontend:**
  - Next.js 15+ (App Router) with React 19 and TypeScript.
  - Tailwind CSS + shadcn/ui for accessible, clean styling.
  - Monaco Editor (`@monaco-editor/react`) for desktop-class code editing.
  - Recharts for teacher heatmaps and misconception progression graphs.
  - Lucide React for consistent icons.
- **Backend:**
  - Python 3.12 + FastAPI for high-throughput async REST endpoints.
  - SQLAlchemy 2 + Alembic for type-safe database models and schema migrations.
  - PostgreSQL 16 for robust relational data with JSONB capabilities.
  - Pydantic v2 for strict request/response data contracts and validation.
  - Pytest + HTTPX for backend test automation.

### Consequences
- **Pros:** Single-language ecosystem for AI/ML and backend (Python); industry-standard frontend stack for modern developer tools.
- **Cons:** Requires running both Node.js and Python development processes locally.

---

## ADR-006: Authoritative Taxonomy Integrity (30 Core Classes + 2 Meta-Classes)

### Context
The original specification documents reference a "27-misconception taxonomy" while explicitly listing categories A through G that contain 30 distinct classes (`A1`–`A5`, `B1`–`B5`, `C1`–`C5`, `D1`–`D5`, `E1`–`E4`, `F1`–`F3`, `G1`–`G3`), plus `S1` (slip) and `S2` (novel).

### Decision
- Formally document the taxonomy discrepancy: categories A through G constitute **30 authoritative core misconception classes**.
- Preserving all 30 core classes intact without arbitrarily deleting, merging, or renaming any.
- Maintain `S1` (Careless slip) and `S2` (Novel / unclassified pattern) as explicitly documented meta-classes, totaling 32 taxonomy entities.

### Consequences
- **Pros:** Eliminates ambiguity; protects domain integrity and pedagogical coverage.
- **Cons:** Benchmark datasets and detectors must support the complete 30-class matrix.

---

## ADR-007: Primary PostgreSQL Database & SQLite Development-Only Policy

### Context
Developers need to run early iterations locally even if Docker is temporarily offline. However, production and testing require full PostgreSQL compliance.

### Decision
- **PostgreSQL 16** is the primary, production target database.
- **SQLite (aiosqlite)** is used strictly as a development convenience for local bootstrapping when Docker is stopped.
- All schema migrations (Alembic) and database-specific behaviors (such as JSONB queries and concurrency) must be tested against PostgreSQL before claiming production readiness.

### Consequences
- **Pros:** Fast zero-friction local development without sacrificing production PostgreSQL standards.
- **Cons:** Must maintain dialect compatibility in SQLAlchemy models.

---

## ADR-008: Authentication, Authorization (RBAC) & Session Management

### Context
CodeRazz requires a secure, production-grade identity and access control foundation. In accordance with our zero-budget mandate, no paid third-party auth services (Auth0, Clerk, Firebase, AWS Cognito) may be introduced. Authentication must support four distinct personas (Student, Teacher, Annotator, Admin) with rigid role separation, protection against privilege escalation, and session revocation capabilities.

### Decision
1. **Password Hashing:**
   - Standardize on **Argon2id** via `argon2-cffi` for password hashing and verification, satisfying modern OWASP password storage requirements.
   - Plaintext passwords and password hashes are never exposed through API responses.
2. **Token & Session Architecture:**
   - **Access Tokens:** Short-lived JSON Web Tokens (JWT, 30-minute validity) signed using HMAC-SHA256 (`HS256`) and an application secret key. Decoded and validated via FastAPI dependency `get_current_user`.
   - **Refresh Tokens:** High-entropy cryptographically random strings (`secrets.token_urlsafe(48)`), stored solely as SHA-256 hashes (`token_hash`) in the `refresh_tokens` database table with expiration timestamps and `revoked` boolean flags.
   - **Token Rotation & Revocation:** Every refresh request invalidates the consumed refresh token and issues a newly rotated pair, preventing replay attacks. Explicit logout marks tokens as revoked.
3. **Role-Based Access Control (RBAC):**
   - Four distinct roles: `STUDENT`, `TEACHER`, `ANNOTATOR`, `ADMIN`.
   - RBAC is strictly enforced on backend FastAPI endpoints using dependency injection (`require_role(*roles)`), returning `403 Forbidden` for unauthorized role attempts.
4. **Privilege Escalation Prevention:**
   - Public registration (`/api/v1/auth/register`) only accepts `STUDENT` or `TEACHER` roles (defaulting to `STUDENT`). Any attempt to submit `ADMIN` or `ANNOTATOR` during registration or user profile self-update is rejected with `400 Bad Request`.
   - Initial system administrator is bootstrapped via offline CLI script (`scripts/create_admin.py`).
   - Subsequent role changes require an authenticated `ADMIN` calling `PUT /api/v1/auth/users/{user_id}/role`.

### Consequences
- **Pros:** Zero-cost, 100% self-hosted, OWASP-compliant, secure session lifecycle with instant revocation capability, and server-side RBAC protection.
- **Cons:** Secret key management must be strictly handled through `.env` configurations; database lookups are required for refresh token rotation.

---

## ADR-009: Ephemeral Docker Execution Sandbox & Confidential Test Case Isolation

### Context
Phase 3 enables student code execution. Executing untrusted student code on the host machine invites catastrophic security vulnerabilities (fork bombs, system compromise, network port scanning, secret exfiltration). Furthermore, grading integrity requires that confidential test cases remain secret from students while providing immediate feedback on sample test cases.

### Decision
1. **Isolated Disposable Linux Runner Image:**
   - Standardized on `coderazz-python-runner:latest` (built on Alpine Linux 3.12, 18.1 MB).
   - Dedicated unprivileged user `coderazz` (`uid=10001:10001`).
   - Every single run or test case evaluation executes in a newly launched, disposable container (`--rm`).
2. **Container Security Hardening:**
   - `--network none` (network severed, egress/ingress impossible).
   - `--read-only` (immutable root filesystem, preventing file overwrites).
   - `--tmpfs /tmp:rw,noexec,nosuid,size=16m` (strictly in-memory scratch space, no execution allowed).
   - `--cap-drop=ALL` (strips all Linux capabilities including `CAP_NET_RAW`, `CAP_SYS_ADMIN`).
   - `--security-opt=no-new-privileges` (prevents SUID privilege escalation).
   - Hard CPU ceiling (`--cpus 1.0`), memory ceiling (`--memory 128m`), and process limit (`--pids-limit 32`).
   - Dual timeout watchdog (3.0s wall-clock max) with asynchronous process termination and container force kill.
   - Runaway stdout/stderr output truncation capped at 64 KB (`65536` bytes).
3. **No Secret or Host Socket Mounts:**
   - Execution containers are mounted with ONLY the student's isolated temporary Python script (`/app/solution.py:ro`).
   - Under no circumstances shall application `.env` files, database credentials, or host Docker socket (`docker.sock`) be mounted.
4. **Offline / Fallback Security Policy:**
   - If the Docker daemon is offline or unavailable, execution requests return `503 Service Unavailable`.
   - The system **never** silently falls back to running untrusted student code on the host machine.
5. **Confidential Test Case Masking:**
   - Public problem endpoints (`GET /api/v1/problems/{id_or_slug}`) strictly filter out test cases where `is_hidden=True`.
   - Hidden test case inputs, expected outputs, and actual outputs are masked from student responses during grading to preserve evaluation integrity.
   - Cross-student submission authorization ensures students can only inspect their own submission records (`403 Forbidden` on unauthorized peer access).

### Consequences
- **Pros:** Robust isolation against hostile scripts (infinite loops, memory bombs, network attempts, filesystem writes, fork bombs); grading integrity protected against test-case reverse-engineering.
- **Cons:** Docker container startup incurs ~150-300ms overhead per test case evaluation run.


