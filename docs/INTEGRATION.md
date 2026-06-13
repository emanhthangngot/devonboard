# INTEGRATION.md — End-to-End DevOnboard Wiring

---

## 1. Local System Map

```text
Browser
  -> Next.js frontend
  -> FastAPI backend
  -> Git/GitHub/LLM services
  -> devonboard/knowledge-graph.json
  -> optional Qdrant/SQLite indexes
```

---

## 2. Startup Sequence

1. Create `.env`.
2. Clone or choose target repo.
3. Start backend.
4. Start frontend.
5. Run scan.
6. Run history ingest.
7. Query and benchmark.

---

## 3. Environment Variables

```bash
TARGET_REPO_PATH=./target_repo
DEVONBOARD_GRAPH_PATH=./devonboard/knowledge-graph.json
GITHUB_TOKEN=...
GEMINI_API_KEY=...
MAX_COMMITS_INGEST=500
QDRANT_URL=http://localhost:6333
BACKEND_URL=http://localhost:8000
```

---

## 4. End-to-End Pipelines

### Scan Pipeline

```text
POST /scan
  -> file inventory
  -> symbol/import extraction
  -> structural graph merge
  -> graph save
```

### History Pipeline

```text
POST /ingest/history
  -> git commit extraction
  -> GitHub metadata fetch
  -> source/entity node creation
  -> rationale claim extraction
  -> provenance edge creation
  -> graph save
```

### Query Pipeline

```text
POST /query or GET /query/stream
  -> route query
  -> retrieve evidence
  -> synthesize answer
  -> return citations
```

---

## 5. Failure Handling

| Failure | Behavior |
|---|---|
| Missing target repo | prompt setup action |
| Missing GitHub token | run commit-only ingest |
| LLM unavailable | return retrieved evidence without synthesis if possible |
| Graph missing | ask user to run scan |
| No evidence | show explicit empty state |

---

## 6. Docker Compose

Docker Compose should run:

- backend;
- frontend;
- optional Qdrant.

The target repo and `devonboard/` graph directory should be mounted as volumes.
