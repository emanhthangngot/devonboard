# copy-tone.md — Microcopy & Tone Rules

> AI.md and constitution.md require the AI layer to be honest about uncertainty and
> evidence gaps. UI copy must reinforce this, never paper over it.

---

## 1. Voice

- Direct, technical, peer-to-peer engineer tone. No marketing adjectives
  ("powerful", "seamless", "magical").
- Second person ("you") for instructions; first person plural avoided ("we").
- Sentences short. Avoid hedging filler ("It looks like maybe...").

---

## 2. Evidence & Uncertainty Language

- Never say "I'm confident" or "definitely" for AI-generated rationale — instead
  state what evidence supports the claim and its confidence score when relevant.
- When evidence is missing, say so explicitly and name what's missing:
  - Good: "No historical evidence found for this query."
  - Bad: "I don't have enough information right now."
- Low-confidence claims: "Low confidence (0.52) — based on a single commit subject
  line with no PR or review context."

---

## 3. Error & Warning Messages

- Name the specific failure and, where possible, the fix:
  - Good: "GitHub token invalid — falling back to commit-only history ingest."
  - Bad: "Something went wrong."
- Stale graph banner: "Graph last updated {date}. Re-run scan/ingest for current data."
- Private repo / external LLM disabled: "External LLM is disabled for this repository
  (`ALLOW_EXTERNAL_LLM_FOR_PRIVATE_REPO=false`). Showing evidence-only results."

---

## 4. Empty States

- Always include the cause and the next action:
  - "No graph found. Run `devonboard scan --repo target_repo` or click Run Scan."
  - "No linked commits found for this node."
  - "Select a file, function, or module to see its History/Why context."

---

## 5. Labels & Buttons

- Buttons describe the action, not the system: "Run Scan", "Generate Evidence Pack",
  "Mark as unsupported", "Retry with narrower scope" — not "Submit" or "OK" alone.
- Mode selector labels: "Auto", "Structural", "Historical", "Hybrid" — match
  `QueryRequest.mode` literals exactly (case may differ for display, value must not).

---

## 6. Numbers & Units

- Always show units for time/latency (`ms`, `s`), and counts with their referent
  ("3 citations", "12 commits") — never bare numbers.
- Confidence/scores shown to 2 decimal places (e.g. `0.84`), not rounded percentages,
  to match `data-model.md` field types.
