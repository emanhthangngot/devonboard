# AI.md — Routing, Rationale Extraction, and Grounded Synthesis

---

## 1. AI Responsibilities

DevOnboard uses AI for:

1. Query routing.
2. Rationale extraction from source evidence.
3. Grounded answer synthesis.
4. Optional subsystem summaries.

AI must not invent design history or replace evidence retrieval.

AI is a copilot, not an autopilot. It helps users inspect evidence and form decisions; it never makes code changes or hides uncertainty.

External LLM calls must use the smallest retrieved context needed for the answer. Secrets, `.env` files, generated artifacts, vendor directories, and full private repositories are excluded from AI context by default.

---

## 2. Query Routing

Output:

```json
{
  "route": "hybrid",
  "node_hints": ["ProviderAdapter"],
  "file_hints": ["internal/providers/adapter.go"],
  "confidence": 0.84
}
```

Route definitions:

- `structural`: how code works, dependencies, call flow, implementation.
- `historical`: why, when, who, decisions, alternatives, PR/commit context.
- `hybrid`: refactor safety, evolution, risk, "full context" questions.

When uncertain, choose `hybrid`.

---

## 3. Rationale Extraction

Run extraction on commit bodies, PR descriptions, review comments, and issue discussions.

Create claims only for explicit:

- rationale;
- tradeoff;
- rejected alternative;
- risk;
- migration;
- compatibility decision;
- performance/security decision.

Structured output:

```json
{
  "claims": [
    {
      "name": "Pipeline stages should be independently testable",
      "summary": "The pipeline was split to make each stage independently testable.",
      "confidence": 0.86,
      "source_node_ids": ["source:pr:341"],
      "tags": ["pipeline", "testability"]
    }
  ]
}
```

Discard claims without source evidence.

---

## 4. Synthesis Rules

Answers must:

- use only retrieved evidence;
- cite structural and historical claims;
- separate "How it works" and "Why / History" when both are present;
- state missing evidence explicitly;
- avoid vague confidence language when citations are available.
- expose enough context for the user to verify important claims.

Recommended sections for hybrid answers:

```markdown
**Structural impact**
...

**Historical context**
...

**Refactor guidance**
...
```

---

## 5. Rejection Rules

The AI layer must refuse or downgrade output when:

- a rationale claim has no source evidence;
- retrieved context is empty;
- evidence is stale or partial and the user asks for high-confidence guidance;
- the answer would require changing code automatically;
- the prompt asks for hidden assumptions not supported by repository evidence.
- the requested context would expose private/proprietary source to an external LLM without explicit opt-in.

In these cases, the answer should state what evidence is missing and suggest the next verification step.

---

## 6. Benchmark Baseline

Plain-agent mode receives only README and file listing context. DevOnboard mode receives graph-retrieved structural and historical evidence. Compare the outputs by citation quality, evidence coverage, and answer usefulness.

`evidence_usefulness_score` is computed automatically from retrieved evidence coverage, direct citations, evidence diversity, and absence of unsupported claims as defined in `docs/RAG.md`. `human_quality_score` is a manual 1-5 rating entered by the evaluator.

Use this fixed MVP query set:

1. Structural onboarding: "How does the agent pipeline execute a tool call?"
2. Design rationale: "Why was progressive memory loading chosen?"
3. Refactor risk: "Is it safe to refactor ProviderAdapter?"
4. PR review prep: "What should I inspect before reviewing changes touching ProviderAdapter?"
5. AI-agent context: "Create a cited context pack for an agent modifying the provider subsystem."
