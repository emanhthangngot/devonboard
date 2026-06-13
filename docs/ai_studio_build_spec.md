# DevOnboard AI Studio Build Specification

This document serves as the comprehensive engineering design and implementation guide for building, running, and testing the **DevOnboard** codebase onboarding system. It contains the complete architectural blueprints, data schemas, API specifications, and flowcharts required to construct or verify DevOnboard in Google AI Studio or other developer environments.

---

## 1. System Overview & Core Workflow

DevOnboard scans a repository, ingests development history, extracts design rationale, and builds a local knowledge graph that answers how the code works, why it was designed that way, and what risks matter before refactoring.

```
       [Target Repo Path]
               │
               ▼
     [Structure Scanner]  ──(Scans files & imports)──► [Knowledge Graph Store]
               │                                                ▲
               ▼                                                │
       [History Ingestion] ──(Ingests Git & PRs)───────────────┤
               │                                                │
               ▼                                                │
     [Rationale Extractor] ──(Gemini Rationale Claims)──────────┘
               │
               ▼
      [Hybrid Retrieval] ◄──(Routes & Traverses Graph)──► [Q&A panel / UI]
               │
               ▼
      [Answer Synthesis] ◄──(Grounded SSE Streaming)
```

### Key Principles
1. **Durable JSON Graph Store**: The primary knowledge store is a single JSON file (`devonboard/knowledge-graph.json`) that records all structural and historical nodes and edges. SQLite and Qdrant are secondary accelerators.
2. **Conservative Claim Extraction**: To avoid hallucinations, the LLM rationale extraction pipeline only creates `claim` nodes when explicit tradeoffs, rationale, rejected alternatives, or compatibility risks are present in the commit bodies/PR descriptions.
3. **Graph-First Hybrid Retrieval**: Answers to hybrid queries traverse direct code structure calling edges first, then pivot to historical commits, PRs, and claims via provenance edges.

---

## 2. Directory Structure & Key Files

The codebase is organized into a Python FastAPI backend and a Next.js TypeScript frontend:

```text
├── 00_problem_statement.md         # Problem context and references
├── 01_market_and_domain/            # Market analysis docs
├── 02_theme_deep_dive/              # Deep dive on codebase memory themes
├── 03_target_users/                 # User Persona documents
├── 04_case_studies/                 # Codebase analysis case studies
├── 05_use_cases/                    # System scenarios
├── AGENTS.md                        # Local workflows and instructions
├── Makefile                         # Unified command interface
├── pyproject.toml                   # Backend packaging (uv-managed)
├── uv.lock                          # Backend lockfile
├── package.json                     # Frontend packaging
├── package-lock.json                # Frontend lockfile
├── docs/                            # Architectural design documents
│   ├── ARCHITECTURE.md              # Backend & Frontend high level architecture
│   ├── BACKEND.md                   # Detailed backend module design
│   ├── FRONTEND.md                  # Frontend visual details
│   ├── AI.md                        # LLM prompting & route definitions
│   ├── RAG.md                       # Retrieval-Augmented Generation spec
│   ├── PROVENANCE_GRAPH.md          # Traceability nodes and edges
│   ├── data-model.md                # Node and Edge type specifications
│   ├── api-spec.json                # OpenAPI specification (JSON)
│   └── ai_studio_build_spec.md      # This file
├── backend/
│   ├── Dockerfile                   # Docker setup for API container
│   ├── app/
│   │   ├── config.py                # Environment variables configuration
│   │   ├── main.py                  # API entry point & CORSMiddleware
│   │   ├── graph/
│   │   │   ├── models.py            # Graph models (Pydantic)
│   │   │   ├── graph_store.py       # Thread-safe JSON persistence
│   │   │   └── ids.py               # Deterministic ID helper functions
│   │   ├── ingest/
│   │   │   ├── git_extractor.py     # Git log parsing
│   │   │   └── rationale_extractor.py # Gemini-powered rationale claim extractor
│   │   ├── scanner/
│   │   │   └── structure_scanner.py # Code parser (extracts files, modules, classes, functions)
│   │   ├── services/
│   │   │   ├── retrieval.py         # Structural, Historical, and Hybrid RAG
│   │   │   ├── evidence_pack.py     # Generates markdown docs for PR reviews / agent context
│   │   │   └── benchmark.py         # Evaluation benchmark orchestrator
│   │   └── routers/
│   │       ├── scan.py              # POST /scan, GET /scan/status
│   │       ├── ingest.py            # POST /ingest/history, GET /ingest/history/status
│   │       ├── graph.py             # GET /graph, GET /graph/node/{id}/history
│   │       ├── query.py             # POST /query (SSE answer synthesis)
│   │       ├── evidence_packs.py    # POST /evidence-packs
│   │       └── benchmark.py         # POST /benchmark, GET /benchmark/results
│   └── tests/                       # Pytest backend tests
├── frontend/
│   ├── Dockerfile                   # Docker setup for UI container
│   ├── tsconfig.json                # TS compiler configuration
│   ├── app/
│   │   ├── page.tsx                 # Core workspace UI (Files list + Q&A + Inspector)
│   │   ├── styles.css               # Main visual styling
│   │   ├── layout.tsx               # Next.js app layout
│   │   └── benchmark/
│   │       └── page.tsx             # Benchmark chart dashboard
│   └── test/                        # Vitest frontend tests
└── devonboard-design/               # Styling tokens, UX flows, components
```

---

## 3. Data Model & Graph Contract

The knowledge graph and related models are defined in [backend/app/graph/models.py](file:///home/pearspringmind/Hackathon/devonboard/backend/app/graph/models.py).

### Node Schema
Nodes are defined as:
```typescript
interface GraphNode {
  id: string;        // Formatted deterministic identifier
  type: NodeType;    // Node category
  name: string;      // Human readable title
  summary: string;   // Brief details
  tags: string[];    // Metadata categories
  filePath?: string; // Relative path (where applicable)
  lineRange?: [number, number]; // Location in file
  metadata: Record<string, any>; // Variable context
}
```

**Node Types (`NodeType`):**
- **Structural**: `file`, `function`, `class`, `module`, `service`, `endpoint`, `config`, `domain`, `flow`, `step`
- **Historical**: `source` (commit, PR, issue, review comment), `claim` (rationale, tradeoff), `entity` (author, reviewer), `topic` (subsystem concept)

**Deterministic ID formats:**
- `file:{filePath}`
- `function:{filePath}:{functionName}`
- `class:{filePath}:{className}`
- `source:commit:{commit_hash}`
- `source:pr:{pr_number}`
- `claim:{slugified_claim_name}`
- `entity:github:{username}`

### Edge Schema
Edges are defined as:
```typescript
interface GraphEdge {
  id: string;        // "{source} -> {target} [{type}]"
  source: string;    // ID of start node
  target: string;    // ID of end node
  type: EdgeType;    // Relationship type
  summary?: string;  // Relationship description
  weight: number;    // Relational strength (default 1.0)
  metadata: Record<string, any>;
}
```

**Edge Types (`EdgeType`):**
- **Structural**: `contains`, `imports`, `calls`, `depends_on`, `implements`, `routes`, `configures`, `contains_flow`, `flow_step`
- **Provenance**: `cites` (claims/docs cite commits/PRs), `documents` (commits document files), `authored_by` (commits authored by users), `exemplifies` (sources support claims), `builds_on` (claims build on claims), `contradicts` (claims contradict claims), `related` (general links)

---

## 4. Backend Implementation & API Details

### Key Services

#### A. Codebase Structure Scanner ([backend/app/scanner/structure_scanner.py](file:///home/pearspringmind/Hackathon/devonboard/backend/app/scanner/structure_scanner.py))
- Inventories files, excluding paths in `EXCLUDE_PATTERNS`.
- Parses files (e.g. Go, Python, TS/JS) extracting imports, functions, classes, and scopes.
- Creates directory structures as `module` nodes.
- Adds `imports` and `contains` edges.

#### B. History Ingester & Git Extractor ([backend/app/ingest/git_extractor.py](file:///home/pearspringmind/Hackathon/devonboard/backend/app/ingest/git_extractor.py))
- Reads `git log` output, parsing the hash, author, date, subject, and files modified.
- Generates `source` nodes for commits, `entity` nodes for authors.
- Creates `documents` edges linking commits to modified `file` nodes.

#### C. Rationale Extractor ([backend/app/ingest/rationale_extractor.py](file:///home/pearspringmind/Hackathon/devonboard/backend/app/ingest/rationale_extractor.py))
- Uses **Gemini API** with structured prompting to parse commit descriptions and PR text.
- Filters out day-to-day noise. Extracts only explicit design decisions, tradeoffs, and architectural changes.
- Output schema parses into `claim` nodes, which are linked to the commit/PR using `exemplifies` and `cites` edges.

#### D. Hybrid Retriever ([backend/app/services/retrieval.py](file:///home/pearspringmind/Hackathon/devonboard/backend/app/services/retrieval.py))
- **Auto Route**: Classifies queries via LLM or regex hints into `structural`, `historical`, or `hybrid`.
- **Hybrid Traversal**:
  1. Identifies starting structural nodes (files, classes, functions) using text search or exact path hints.
  2. Expands traversal via structural connections (`calls`, `depends_on`).
  3. Steps across provenance edges (`documents`, `cites`) to gather related commits, PR reviews, and authors.
  4. Collects rationale `claims` linked to those sources.
  5. Scores and ranks the collected evidence pool based on connectivity strength and recency.

#### E. Grounded Answer Synthesizer ([backend/app/routers/query.py](file:///home/pearspringmind/Hackathon/devonboard/backend/app/routers/query.py))
- Packages the ranked structural and historical evidence.
- Feeds them to Gemini with a strict system instruction: **Answer the user query using ONLY the provided evidence. Cite node IDs (e.g. `[source:commit:abcd]`) directly. Refuse or warning-tag claims unsupported by the evidence.**
- Streams the synthesized markdown answer with structural and historical sections.

---

## 5. API Endpoints

The API is fully documented in [docs/api-spec.json](file:///home/pearspringmind/Hackathon/devonboard/docs/api-spec.json).

| Path | Method | Description |
|---|---|---|
| `/health` | `GET` | Service status, graph file existence, Gemini API accessibility |
| `/scan` | `POST` | Trigger repository structural scanning |
| `/scan/status` | `GET` | Get scan progress and status |
| `/ingest/history` | `POST` | Trigger Git history parsing & Gemini rationale extraction |
| `/ingest/history/status`| `GET` | Get ingest status |
| `/query` | `POST` | Route and answer a codebase question with citations |
| `/graph` | `GET` | Return the full knowledge graph nodes & edges |
| `/graph/node/{id}/history`| `GET` | Fetch specific history (commits, authors, claims) for a selected node |
| `/evidence-packs` | `POST` | Generate copyable markdown packs for PR reviews or agent tasks |
| `/benchmark` | `POST` | Trigger evaluation comparison runs |
| `/benchmark/results` | `GET` | List saved evaluation run statistics |

---

## 6. Frontend Layout & Design System

The frontend is built with React and Tailwind-free vanilla CSS. It follows a projector-friendly, dense information layout optimized for codebase investigation.

### 1. Main Workspace Layout (`frontend/app/page.tsx`)
- **Top Bar**: Shows repository metadata and buttons to run **Run Scan** and **Ingest History**.
- **Left Panel (File tree/Graph Nav)**: Lists files and modules in the graph. Active node can be selected.
- **Middle Panel (Q&A Interface)**: Text input with quick-select developer queries, streaming answer display, and inline citation cards.
- **Right Panel (History/Why Inspector)**: Displays the selected node details, its direct author/reviewers, commits affecting it, and extracted design claims or risks.

### 2. Benchmark Dashboard (`frontend/app/benchmark/page.tsx`)
- Displays run histories comparing **DevOnboard** (hybrid-retrieved context) vs **Plain Agent** (README + folder structure only).
- Compares latency, citation coverage, token usage, and computed usefulness scores.

---

## 7. Setup & Run Instructions

### Configuration (`.env`)
Create a `.env` in the root:
```bash
GEMINI_API_KEY=AIzaSy...              # Get from Google AI Studio
GITHUB_TOKEN=ghp_...                  # Recommended for GitHub API calls
TARGET_REPO_PATH=./target_repo        # Target repo to analyze
DEVONBOARD_GRAPH_PATH=./devonboard/knowledge-graph.json
```

### Option A: Local Dev
1. Install uv (Python) and npm (Node.js).
2. Install all dependencies:
   ```bash
   make install
   ```
3. Start backend FastAPI:
   ```bash
   make dev
   ```
4. Start frontend Next.js:
   ```bash
   npm run dev --prefix frontend
   ```

### Option B: Docker Compose
Build and start backend, frontend, and optional Qdrant services:
```bash
docker compose up --build
```

---

## 8. Verification & Tests

Ensure the setup is verified by executing:
- Run all test suites: `make test`
- Backend unit tests: `make test-backend`
- Frontend unit tests: `make test-frontend`
- End-to-end integration smoke tests: `make e2e`
