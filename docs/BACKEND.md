# BACKEND.md — FastAPI Backend Design

---

## 1. Service Layout

```text
backend/app/
├── main.py
├── config.py
├── scanner/
├── ingest/
├── graph/
├── services/
└── routers/
```

Core routers:

- `POST /scan`
- `POST /ingest/history`
- `POST /query`
- `GET /query/stream`
- `GET /graph`
- `GET /graph/node/{id}/history`
- `POST /evidence-packs`
- `POST /benchmark/run`
- `GET /benchmark/results`

---

## 2. Scanner Services

Responsibilities:

- walk repository files;
- apply ignore rules;
- extract file, module, function, class, import, and config nodes;
- create structural edges;
- write graph updates through `GraphStore`.

Scanner should degrade to file-level graph data when detailed symbol extraction fails.

---

## 3. History Ingest Services

Responsibilities:

- call Git CLI for commits and changed files;
- call GitHub API for PR/review/issue metadata when token exists;
- create `source` and `entity` nodes;
- link sources to files/functions/modules.

Commit-only ingest is a valid fallback.

---

## 4. Graph Services

`GraphStore` owns:

- load/save JSON;
- node/edge upsert;
- deterministic ID helpers;
- file path lookup;
- node history traversal;
- optional SQLite index rebuild.

`GraphQuery` owns:

- structural search;
- historical search;
- hybrid traversal;
- evidence ranking.

---

## 5. AI Services

`RouterService` classifies query route.

`RationaleExtractor` creates claim candidates from source evidence.

`SynthesisService` creates blocking and streaming answers from retrieved evidence.

All AI calls must use retry/backoff and must expose errors clearly.

---

## 6. Benchmark Service

Benchmark service:

- loads fixed query set;
- runs DevOnboard and plain-agent modes;
- records time-to-useful-answer, evidence count, citation count, token estimates, evidence usefulness score, and human quality score;
- writes immutable JSON results.

Evidence pack service:

- creates PR review and AI-agent context packs from graph evidence;
- excludes secrets, generated/vendor files, and unsupported rationale;
- returns copyable Markdown plus citations and warnings.
