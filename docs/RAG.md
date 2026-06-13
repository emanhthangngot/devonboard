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
2. Resolve classifier `node_hints` against node IDs, names, tags, and summaries.
3. Resolve classifier `file_hints` against `filePath` and file-node IDs.
4. Use matched nodes and hints as traversal seeds.
5. Collect related files/functions/modules through `contains`, `calls`, `imports`, `depends_on`, `implements`, `routes`, `contains_flow`, and `flow_step` edges.
6. Traverse provenance edges to sources and claims.
7. Expand with semantic search if enabled.
8. Rank evidence and assemble answer context.

`node_hints` and `file_hints` do not override graph retrieval. They bias the starting set for BFS and ranking. If a hint does not resolve to a graph node, keep it in `warnings[]` and continue with text/path matching.

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

## 7. Evidence Pack Generation

Evidence packs use the same graph-first retrieval pipeline as query answers, but optimize the Markdown output for the requested purpose.

### `pr_review`

Inputs should include `changed_files`, `node_ids`, or a review-oriented `query`. The service should:

- seed traversal from changed files and directly selected nodes;
- include structural blast radius: callers, dependencies, routes, flows, and neighboring modules;
- include recent linked commits, PRs, issues, reviews, claims, risks, and contradictions;
- group Markdown as `Changed scope`, `Structural impact`, `Historical context`, `Risks / review questions`, and `Citations`;
- prefer reviewer-actionable warnings over broad summaries.

### `ai_agent_context`

Inputs should include `node_ids`, `changed_files`, or a task query. The service should:

- include only the smallest relevant structural and historical context needed for the agent task;
- include interfaces, files, constraints, known risks, and cited rationale;
- exclude secrets, generated/vendor files, unsupported claims, and unnecessary raw code;
- use evidence-only mode when the repository is private and `ALLOW_EXTERNAL_LLM_FOR_PRIVATE_REPO=false`;
- group Markdown as `Task context`, `Relevant files/interfaces`, `Historical constraints`, `Do not assume`, and `Citations`.

Both pack types return `citations`, `warnings`, and `excluded_sources`. Unsupported rationale is excluded rather than summarized.

---

## 8. Evidence Usefulness Score

`evidence_usefulness_score` is a deterministic computed 1-5 score used by benchmark runs. `human_quality_score` remains a manual human rating.

Recommended formula:

```text
score = clamp_1_5(round(
  1
  + 1.0 * has_direct_structural_evidence
  + 1.0 * has_direct_historical_evidence
  + 1.0 * citation_coverage
  + 0.5 * evidence_diversity
  + 0.5 * no_unsupported_claims
))
```

Where:

- `has_direct_structural_evidence` is 1 when the answer cites at least one file/function/module node required by the query.
- `has_direct_historical_evidence` is 1 when historical or rationale claims cite source/claim nodes.
- `citation_coverage` is the cited evidence count divided by total evidence items, capped at 1.
- `evidence_diversity` is 1 when at least two evidence families are present, such as structural plus PR/commit/claim.
- `no_unsupported_claims` is 1 when no warning reports unsupported or dropped rationale.

---

## 9. Retrieval Guardrails

- Do not synthesize rationale without historical evidence.
- Prefer linked PR/review evidence over commit subject-only evidence.
- Show "no evidence found" when history is absent.
- Keep context windows compact: top 3 structural nodes and top 5 historical evidence items by default.
