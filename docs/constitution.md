# DevOnboard — Project Constitution

> Governing principles for all product, architecture, and implementation documents.

---

## 1. Core Mission

DevOnboard helps engineering teams preserve and retrieve codebase institutional memory. It combines structural code understanding with git/GitHub history and design-rationale extraction so engineers can answer how a system works, why it was built that way, and what risks surround future changes.

---

## 2. Architecture Principles

**P1 — DevOnboard owns the product surface.** The project has its own scanner, graph model, query flow, UI, benchmark, and documentation. External tools may be technical dependencies, but the product identity and public docs stay DevOnboard-native.

**P2 — Evidence before synthesis.** The AI layer may summarize and route, but answers must be grounded in files, commits, PRs, issues, review comments, or graph claims.

**P3 — Graph as durable memory.** `devonboard/knowledge-graph.json` is the primary artifact. Optional indexes such as SQLite or vector search are rebuildable accelerators.

**P4 — History is first-class.** Commits, PRs, review comments, issues, authors, rejected alternatives, and design claims are product data, not append-only notes.

**P5 — Human-verifiable AI.** Every important answer should expose citations and uncertainty. When evidence is missing, say so.

**P6 — Demo reliability.** MVP must work on a prepared repository with bounded scan/ingest size and deterministic benchmark queries.

**P7 — Data handling by default.** DevOnboard must not send secrets, generated/vendor artifacts, or full private repositories to external LLMs. External synthesis uses retrieved snippets only, and private/proprietary repositories require explicit opt-in or evidence-only mode.

---

## 3. Technology Governance

| Concern | Chosen direction | Rationale |
|---|---|---|
| Backend API | FastAPI + Python 3.11+ | Async-friendly, straightforward for git/GitHub/LLM integration |
| Frontend | Next.js + TypeScript | Good local app shell and streaming UI |
| Graph artifact | JSON file plus optional SQLite index | Inspectable, portable, easy to demo |
| History ingest | Git CLI + GitHub REST API | Highest-signal source of development rationale |
| AI | Gemini Flash + embeddings for MVP | Free-tier friendly and sufficient for routing/extraction/synthesis |
| Optional vector DB | Qdrant | Semantic retrieval over source/claim text when graph traversal is not enough |

---

## 4. Quality Standards

**Q1 — Citation completeness.** Historical rationale without a citation is incomplete.

**Q2 — Deterministic IDs.** Graph node IDs must be stable across reruns, e.g. `file:<path>`, `source:commit:<sha>`, `claim:<slug>`.

**Q3 — Idempotent ingest.** Rerunning scan or history ingest must update existing graph entities rather than duplicating them.

**Q4 — Clear boundaries.** Product docs describe what and why. Architecture docs describe how.

**Q5 — No hardcoded secrets.** API keys and tokens live in `.env`; examples use non-secret sample values.

**Q6 — Contract consistency.** OpenAPI, backend docs, data models, and frontend expectations must describe the same endpoints, fields, and error semantics.

---

## 5. Scope Boundaries

- Single-repo, single-user demo scope.
- Public or locally available GitHub metadata only.
- No automatic code modification.
- No production authorization, billing, or enterprise admin controls in MVP.
- No default external LLM processing for private repositories without user opt-in.
