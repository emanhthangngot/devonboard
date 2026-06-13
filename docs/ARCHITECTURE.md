# DevOnboard — System Architecture

> Source of truth for the standalone DevOnboard architecture.

---

## 1. System Overview

DevOnboard builds a knowledge graph from a target repository and uses it to power onboarding, historical explanation, refactor-risk analysis, and benchmarking.

```text
Target repo
  -> Structure Scanner
  -> Git/GitHub History Ingest
  -> Rationale Extractor
  -> DevOnboard Knowledge Graph
  -> Hybrid Retrieval
  -> Answer Synthesis + UI + Benchmark
```

Primary artifact:

```text
devonboard/knowledge-graph.json
```

Optional derived indexes:

- SQLite for fast node/edge/file lookup.
- Qdrant for semantic retrieval over source and claim text.

---

## 2. Core Components

### Structure Scanner

Reads the repository and creates structural graph data:

- files and directories;
- functions/classes/modules where extractable;
- imports and dependency edges;
- config, endpoint, service, and flow summaries when detectable.

MVP scanner can be pragmatic:

- tree-sitter or language-specific parsers for common languages;
- regex fallback for unsupported files;
- LLM-assisted summaries for subsystem/domain labels;
- ignore generated/vendor/build artifacts.

### History Ingest

Reads development history:

- `git log`;
- commit subject/body;
- files touched;
- author/date;
- PR title/body;
- review comments;
- issue references.

It creates `source` nodes for commits, PRs, review comments, and issues, plus `entity` nodes for authors/reviewers.

### Rationale Extractor

Runs a conservative extraction pass over source evidence and creates `claim` nodes only when text explicitly expresses:

- design rationale;
- tradeoffs;
- rejected alternatives;
- migration/deprecation intent;
- compatibility concerns;
- performance/security decisions;
- known refactor risk.

### Graph Store

Responsible for:

- deterministic IDs;
- merge/idempotency;
- node and edge validation;
- graph persistence;
- optional derived index rebuild.

### Hybrid Retrieval

Routes queries into:

| Route | Evidence |
|---|---|
| Structural | code graph nodes/edges |
| Historical | source/claim/entity/topic nodes |
| Hybrid | structural match first, then linked history |

Hybrid retrieval prefers graph links, then optionally expands with semantic search.

### Answer Synthesis

Builds a grounded prompt with retrieved evidence and streams a concise answer. It must label structural and historical sections when both are present.

---

## 3. Backend Architecture

```text
backend/app/
├── scanner/
│   ├── structure_scanner.py
│   ├── symbol_extractor.py
│   └── graph_builder.py
├── ingest/
│   ├── git_extractor.py
│   ├── github_fetcher.py
│   └── rationale_extractor.py
├── graph/
│   ├── graph_store.py
│   ├── graph_query.py
│   └── graph_index.py
├── services/
│   ├── router.py
│   ├── retrieval.py
│   ├── synthesis.py
│   └── benchmark.py
└── routers/
    ├── scan.py
    ├── ingest.py
    ├── query.py
    └── benchmark.py
```

API surface:

```text
POST /scan
POST /ingest/history
POST /query
GET  /query/stream
GET  /graph
GET  /graph/node/{id}/history
POST /benchmark/run
GET  /benchmark/results
```

---

## 4. Frontend Architecture

The first screen is the usable product workspace:

```text
TopNav: repo, graph status, scan/ingest controls
Main:
  Left  -> graph/file/subsystem navigation
  Center -> Q&A and streamed answers
  Right -> History/Why inspector for selected node
Benchmark tab -> comparison table and charts
```

Required states:

- no repo loaded;
- scanning;
- ingesting history;
- node selected with history;
- node selected with no history;
- query streaming;
- benchmark running.

---

## 5. Data Flow

### Scan

```text
repo path
  -> ignore filter
  -> file inventory
  -> symbol/import extraction
  -> graph nodes/edges
  -> knowledge-graph.json
```

### History Ingest

```text
git history + GitHub metadata
  -> source/entity nodes
  -> file/source provenance edges
  -> rationale claims
  -> claim/source edges
  -> merged graph
```

### Query

```text
user query
  -> route classifier
  -> graph retrieval
  -> optional vector expansion
  -> context assembly
  -> grounded synthesis
  -> citations + answer
```

---

## 6. Design Decisions

### D1 — JSON Graph as Primary Artifact

JSON is easy to inspect, diff, demo, and rebuild. SQLite/Qdrant are implementation accelerators, not authoritative data stores.

### D2 — Conservative Claim Extraction

Wrong rationale is worse than missing rationale. Only explicit design claims should become `claim` nodes.

### D3 — Graph-First Hybrid Retrieval

Graph links explain why evidence is relevant. Vector similarity can expand candidates but should not outrank direct provenance links.

### D4 — Single-Repo MVP

Multi-repo and enterprise permissions add product surface that is not needed for the hackathon demo.

---

## 7. Failure Modes

| Scenario | Behavior |
|---|---|
| Parser cannot extract symbols | Keep file nodes and summarize at file/module level |
| GitHub API unavailable | Commit-only ingest continues |
| No historical evidence | Show explicit empty state |
| LLM extraction uncertain | Store source evidence only; skip claim |
| Vector DB unavailable | Use graph-only retrieval |
| Query too broad | Ask for clarification or return top subsystems with caveat |

---

## 8. Performance Targets

| Metric | MVP target |
|---|---|
| Scan prepared demo repo | under 5 minutes |
| Ingest 500 commits | under 10 minutes |
| Node History panel | under 500 ms from indexed graph |
| Structural answer | under 8 seconds |
| Hybrid answer | under 12 seconds |
