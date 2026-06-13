# RAG.md — Graph-First Retrieval

> Retrieval starts from DevOnboard's knowledge graph. Vector search is optional acceleration, not the source of truth.

---

## 1. Retrieval Overview

```text
User query
  -> route classifier
  -> graph retrieval
  -> optional vector expansion
  -> evidence ranking
  -> grounded synthesis
```

Routes:

- `structural`: code nodes and dependency/call edges.
- `historical`: source, claim, entity, and topic nodes.
- `hybrid`: structural match first, then linked history.

---

## 2. Structural Retrieval

Searches:

- node names;
- file paths;
- tags;
- summaries;
- dependency/call/import edges;
- flow and step relationships.

Outputs structural evidence such as:

- relevant files/functions/modules;
- call/dependency path;
- impacted neighboring nodes.

---

## 3. Historical Retrieval

Searches:

- commit/PR/issue/review `source` nodes;
- extracted `claim` nodes;
- authors/reviewers as `entity` nodes;
- design topics.

Graph traversal:

```text
file/function/module
  -> cites/documents
  -> source
  -> exemplifies/cites
  -> claim
```

---

## 4. Hybrid Retrieval

Hybrid mode is the core workflow for refactor-risk questions:

1. Find structural nodes matching the query.
2. Collect related files/functions/modules.
3. Traverse provenance edges to sources and claims.
4. Expand with semantic search if enabled.
5. Rank evidence and assemble answer context.

---

## 5. Optional Vector Index

Qdrant can index `source` and `claim` text:

```json
{
  "id": "source:pr:341",
  "payload": {
    "graph_node_id": "source:pr:341",
    "doc_type": "pr",
    "files_touched": ["internal/agent/pipeline.go"],
    "date": "2026-03-14T10:22:00Z"
  }
}
```

Vector results must map back to graph node IDs before synthesis.

---

## 6. Ranking

Recommended ranking:

```text
score =
  0.45 * graph_link_strength
+ 0.25 * semantic_similarity
+ 0.20 * source_quality
+ 0.10 * recency
```

Direct graph evidence should outrank vague semantic matches.

---

## 7. Retrieval Guardrails

- Do not synthesize rationale without historical evidence.
- Prefer linked PR/review evidence over commit subject-only evidence.
- Show "no evidence found" when history is absent.
- Keep context windows compact: top 3 structural nodes and top 5 historical evidence items by default.
