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

In these cases, the answer should state what evidence is missing and suggest the next verification step.

---

## 6. Benchmark Baseline

Plain-agent mode receives only README and file listing context. DevOnboard mode receives graph-retrieved structural and historical evidence. Compare the outputs by citation quality, evidence coverage, and answer usefulness.
