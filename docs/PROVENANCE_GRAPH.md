# PROVENANCE_GRAPH.md — DevOnboard Knowledge Graph

---

## 1. Purpose

The provenance graph connects current code artifacts to the development evidence that shaped them.

```text
file/function/module
  -> commit / PR / issue / review
  -> design claim
  -> author / reviewer
  -> risk / rejected alternative
```

This is the core differentiator of DevOnboard.

---

## 2. Evidence Nodes

Use `source` nodes for:

- commits;
- pull requests;
- review comments;
- issues;
- design notes.

Use `claim` nodes for:

- rationale;
- tradeoffs;
- rejected alternatives;
- compatibility risks;
- performance/security decisions.

Use `entity` nodes for:

- authors;
- reviewers;
- teams;
- important libraries or systems.

---

## 3. Provenance Edges

| Edge | Meaning |
|---|---|
| `cites` | artifact cites source evidence |
| `documents` | source explains artifact |
| `authored_by` | source was authored by entity |
| `exemplifies` | source demonstrates claim |
| `builds_on` | later source/claim refines earlier one |
| `contradicts` | claim/source conflicts with another |
| `related` | useful weak relation |

---

## 4. History/Why Panel

For any selected code node, show:

- linked commits;
- linked PRs/issues;
- extracted claims;
- authors/reviewers;
- rejected alternatives;
- risk indicators.

---

## 5. Refactor Risk

Refactor-risk answers combine:

- structural impact: callers, dependencies, modules, flows;
- historical risk: bug-fix commits, rejected alternatives, fragile decisions;
- evidence strength: PR/review evidence outranks vague commit subjects.
