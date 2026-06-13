# Data Model: DevOnboard Knowledge Graph

---

## 1. Graph Contract

```typescript
interface KnowledgeGraph {
  version: string;
  generated_at: string;
  repo: RepoMeta;
  nodes: GraphNode[];
  edges: GraphEdge[];
  benchmark_runs?: BenchmarkRunSummary[];
}
```

Primary file:

```text
devonboard/knowledge-graph.json
```

---

## 2. Node Types

| Type | Meaning |
|---|---|
| `file` | Source or config file |
| `function` | Function or method |
| `class` | Class, struct, interface, or type-like unit |
| `module` | Package, folder, namespace, or logical module |
| `service` | Runtime service or major component |
| `endpoint` | HTTP/API/CLI/event entrypoint |
| `config` | Environment/configuration artifact |
| `domain` | Business or system domain |
| `flow` | Multi-step workflow |
| `step` | Step inside a flow |
| `source` | Commit, PR, issue, review comment, or external evidence |
| `claim` | Extracted design rationale, tradeoff, or risk statement |
| `entity` | Author, reviewer, team, organization, library |
| `topic` | Subsystem theme or concept category |

---

## 3. Core Node Shape

```typescript
interface GraphNode {
  id: string;
  type: NodeType;
  name: string;
  summary: string;
  tags: string[];
  filePath?: string;
  lineRange?: [number, number];
  metadata?: Record<string, unknown>;
}
```

ID examples:

- `file:internal/agent/pipeline.go`
- `function:internal/agent/pipeline.go:ExecutePipeline`
- `source:commit:a3f2b1c9`
- `source:pr:341`
- `source:review:341:ab12cd`
- `claim:pipeline-stages-testable`
- `entity:github:octocat`

---

## 4. Edge Types

| Type | Meaning |
|---|---|
| `contains` | parent contains child |
| `imports` | file/module imports another file/module |
| `calls` | function calls function |
| `depends_on` | artifact depends on another artifact |
| `implements` | implementation satisfies an interface/contract |
| `routes` | endpoint routes to handler |
| `configures` | config affects component |
| `contains_flow` | domain/module contains workflow |
| `flow_step` | flow advances to step |
| `cites` | node cites source evidence |
| `documents` | source explains code artifact |
| `authored_by` | source was authored by entity |
| `exemplifies` | source demonstrates claim |
| `builds_on` | later claim/source builds on earlier one |
| `contradicts` | claim/source conflicts with another |
| `related` | weak contextual relation |

```typescript
interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  summary?: string;
  weight: number;
  metadata?: Record<string, unknown>;
}
```

---

## 5. Historical Source Node

```json
{
  "id": "source:commit:a3f2b1c9",
  "type": "source",
  "name": "refactor: split pipeline into stages",
  "summary": "Changed pipeline execution into separate testable stages.",
  "tags": ["git", "commit", "pipeline"],
  "metadata": {
    "kind": "commit",
    "hash": "a3f2b1c9d4e5",
    "author": "octocat",
    "date": "2026-03-14T10:22:00Z",
    "url": "https://github.com/owner/repo/commit/a3f2b1c9d4e5",
    "filesTouched": ["internal/agent/pipeline.go"]
  }
}
```

---

## 6. Claim Node

```json
{
  "id": "claim:pipeline-stages-testable",
  "type": "claim",
  "name": "Pipeline stages should be independently testable",
  "summary": "The pipeline was split so each stage can be tested and extended independently.",
  "tags": ["design-rationale", "pipeline", "testability"],
  "metadata": {
    "confidence": 0.84,
    "extractedFrom": ["source:pr:341"]
  }
}
```

Claims are created only from explicit source evidence.

---

## 7. Query Models

```python
class QueryRequest(BaseModel):
    query: str
    mode: Literal["auto", "structural", "historical", "hybrid"] = "auto"

class RouteDecision(BaseModel):
    route: Literal["structural", "historical", "hybrid"]
    node_hints: list[str] = []
    file_hints: list[str] = []
    confidence: float = 1.0

class Evidence(BaseModel):
    node_id: str
    type: Literal["file", "function", "commit", "pr", "issue", "review", "claim", "entity"]
    label: str
    summary: str
    url: str | None = None
    score: float | None = None

class QueryResponse(BaseModel):
    answer: str
    route: Literal["structural", "historical", "hybrid"]
    structural: list[Evidence] = []
    historical: list[Evidence] = []
    citations: list[Evidence] = []
    warnings: list[str] = []
    retrieval_ms: int
    synthesis_ms: int

class EvidencePack(BaseModel):
    purpose: Literal["pr_review", "ai_agent_context"]
    markdown: str
    citations: list[Evidence]
    warnings: list[str] = []
    excluded_sources: list[str] = []
```

---

## 8. Benchmark Models

```python
class MetricRow(BaseModel):
    query_id: int
    query_text: str
    mode: Literal["devonboard", "plain_agent"]
    time_to_useful_answer_ms: int
    citations_count: int
    evidence_count: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    evidence_usefulness_score: int | None = None
    human_quality_score: int | None = None

class BenchmarkRun(BaseModel):
    run_id: str
    repo: str
    target_branch: str
    target_commit: str | None = None
    rows: list[MetricRow]
    created_at: datetime
```
