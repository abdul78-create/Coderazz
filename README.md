# CodeRazz: A Misconception-Aware Programming Tutor

> **"Don't just fix the code. Understand the thinking behind it."**

CodeRazz is an open-source, AI-powered educational programming platform. While traditional online judges stop at reporting *Wrong Answer* or *Runtime Error*, CodeRazz diagnoses the **underlying mental model error (misconception)** responsible for a student's bug, delivers a **5-tier progressive hint ladder** without leaking solutions, and equips educators with **class-level misconception analytics**.

---

## 🌟 Key Highlights

- **Zero-Paid-Tools & ₹0 Budget:** Powered completely by free and open-source software (Python 3.12, FastAPI, Next.js 15, PostgreSQL 16, Scikit-learn, Docker, and optional local Ollama).
- **Authoritative Misconception Taxonomy:** Standardized classification across 7 fundamental programming domains containing 30 core misconception classes (`A1`–`G3`), plus 2 meta-classes (`S1` Slip, `S2` Novel pattern), totaling 32 categories.
- **Hybrid Diagnostic Engine:** Combines Abstract Syntax Tree (AST) static analysis, behavioral test traces, targeted diagnostic probes, and modular Scikit-learn classification with configurable evidence-based confidence scoring.
- **5-Level Progressive Hint Ladder:** Guides learners systematically from directional nudges to minimal counter-examples and targeted pointers with an automated `SolutionLeakGuard`.
- **Isolated Sandbox Execution:** Student code is strictly segregated in disposable, non-root containers with hard CPU, memory, time, and network constraints.
- **Teacher & Annotator Portals:** Real-time misconception heatmaps, longitudinal class struggle tracking, and human-in-the-loop diagnostic override queues.

---

## 🏗️ System Architecture

```
CodeRazz/
├── frontend/               # Next.js 15 App Router, React 19, Tailwind CSS, Monaco Editor
├── backend/                # FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, REST APIs
├── execution/              # Sandboxed execution service (Docker & fallback subprocess runner)
├── ml/                     # AST feature extraction, Rule matchers, Diagnostic probes, ML classifiers
├── dataset/                # Taxonomy definitions, benchmark buggy code samples, evaluation data
├── docs/                   # ARCHITECTURE.md, IMPLEMENTATION_PLAN.md, DECISIONS.md, TESTING.md
├── scripts/                # Database seeding, benchmark runners, evaluation utilities
├── tests/                  # Pytest unit, integration, and security test suites
├── docker-compose.yml      # Local development database and container orchestration
├── .env.example            # Environment variables template
├── AGENTS.md               # Persistent AI Agent & engineering protocols
└── README.md               # Project documentation
```

---

## 📊 Authoritative Misconception Taxonomy (30 Core Classes + 2 Meta-Classes)

- **Category A (Loops & Indexing - 5):** `A1` Off-by-one, `A2` Infinite loop, `A3` Index out of range, `A4` Loop variable shadow, `A5` Premature loop exit.
- **Category B (Conditions & Logic - 5):** `B1` Assignment vs equality, `B2` Inverted boolean operators, `B3` Misordered elif, `B4` Indentation branch error, `B5` Redundant/contradictory conditions.
- **Category C (Scope & State - 5):** `C1` Uninitialized variable, `C2` Local/global confusion, `C3` Mutable object alias mutation, `C4` Type mismatch, `C5` Loop variable rebinding.
- **Category D (Functions & Recursion - 5):** `D1` Missing base case, `D2` Missing explicit return, `D3` Argument order inversion, `D4` Return inside loop, `D5` No argument reduction.
- **Category E (Data Structures - 4):** `E1` Mutating during iteration, `E2` Unchecked dict key, `E3` Shallow copy confusion, `E4` Non-subscriptable object indexing.
- **Category F (Algorithms & Efficiency - 3):** `F1` Premature accumulator reset, `F2` Inefficient lookup (TLE), `F3` Unstable sort assumption.
- **Category G (I/O & Language - 3):** `G1` Print instead of return, `G2` Unparsed input type, `G3` In-place string mutation.
- **Meta-Classes (2):** `S1` Careless slip / typo, `S2` Novel / unclassified pattern.

---

## 🔒 Security & Code Execution

Student code is treated as strictly untrusted:
- Disposable Docker container execution per run.
- Non-root user execution (`uid=10001:10001`).
- Completely severed network access (`--network none`).
- Read-only root filesystem with restricted 16MB `tmpfs` mounted `noexec`.
- Dropped Linux capabilities (`--cap-drop=ALL`) and `--security-opt=no-new-privileges`.
- Hard resource bounds: 1 CPU core, 128 MB RAM, max 32 PIDs, 3.0s wall-clock timeout.
- Zero secret mounting: Application source, `.env`, credentials, and `docker.sock` are never mounted into containers.
- **Host Subprocess Warning:** Host subprocess fallback is strictly restricted to trusted local development smoke tests and does not form a security boundary for student code.
- Public deployment requires kernel-gated runtimes (gVisor or Firecracker).

---

## 🚀 Getting Started

### Prerequisites
- Node.js (v22 LTS recommended)
- Python (v3.12+)
- Docker Desktop (recommended for containerized execution & PostgreSQL)

### Setup & Run
1. Copy configuration:
   ```bash
   cp .env.example .env
   ```
2. Start PostgreSQL:
   ```bash
   docker compose up -d db
   ```
3. Initialize Backend & Run Tests:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r backend/requirements.txt
   pytest
   ```
4. Start Frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## 📖 Living Documentation Links

- [System Architecture Specification](file:///c:/Users/Abdul/Desktop/Coderazz/docs/ARCHITECTURE.md)
- [Architectural Decision Records (ADRs)](file:///c:/Users/Abdul/Desktop/Coderazz/docs/DECISIONS.md)
- [Implementation Plan & Checklists](file:///c:/Users/Abdul/Desktop/Coderazz/docs/IMPLEMENTATION_PLAN.md)
- [Testing & Security Verification Strategy](file:///c:/Users/Abdul/Desktop/Coderazz/docs/TESTING.md)
- [Agent Engineering Rules (AGENTS.md)](file:///c:/Users/Abdul/Desktop/Coderazz/AGENTS.md)
