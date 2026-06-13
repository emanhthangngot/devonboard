# Research: DevOnboard Technology and Product Validation

**Last updated:** 2026-06-12

---

## 1. AI-Assisted Development Creates A Context Gap

### Verdict: DevOnboard should focus on evidence, not raw code generation

AI coding tools can speed up bounded programming tasks, but production engineering still depends on context, review, and safe change management. A GitHub Copilot controlled study found a 55.8% faster completion time for a scoped JavaScript task. DORA research cautions that AI adoption must be paired with strong delivery and verification practices.

Design implication: DevOnboard's value is not writing code. Its value is giving humans and AI agents trustworthy, cited context before code changes happen.

---

## 2. Git And Pull Requests Are High-Signal Memory

### Verdict: Ingest git/GitHub history as first-class product data

The most valuable historical evidence usually appears in:

- PR descriptions explaining intent;
- review comments debating alternatives;
- issue threads documenting bugs or regressions;
- commit bodies describing migrations;
- changed-file lists showing which code areas were affected.

Design implication: DevOnboard should model commits, PRs, issues, and reviews as graph `source` nodes linked to current code artifacts.

---

## 3. Graph-First Retrieval Is More Explainable Than Vector-Only Search

### Verdict: Use graph as the durable memory layer

Vector search can retrieve semantically similar history, but graph edges explain why evidence is relevant. For onboarding and refactor-risk questions, relevance must be inspectable.

Design implication:

- Store durable evidence in `devonboard/knowledge-graph.json`.
- Use optional vector search only to expand candidates.
- Map vector results back to graph nodes before synthesis.

---

## 4. Rationale Extraction Must Be Conservative

### Verdict: Missing a weak claim is better than creating a false one

Create `claim` nodes only when source text explicitly signals:

- rationale;
- tradeoff;
- rejected alternative;
- risk;
- migration;
- compatibility concern;
- performance/security decision.

Skip claims for routine implementation, dependency bumps, formatting, and vague commit subjects.

---

## 5. Benchmark Design

Compare:

- **Plain agent:** README + file listing only.
- **DevOnboard:** graph-retrieved structural and historical evidence.

Metrics:

- latency;
- citation count;
- evidence count;
- structural correctness;
- historical rationale quality;
- human quality score.

The benchmark should show whether DevOnboard improves trust and evidence coverage, not just answer speed.

---

## 6. DVF Assessment Notes

### Desirability

Target users already experience onboarding and review friction. The strongest evidence is behavioral: engineers manually combine grep, GitHub search, `git blame`, PR reading, and senior-engineer questions today.

### Viability

The product has a credible wedge because it combines repository data the team already owns with AI synthesis. Its value should be measured by task success, time saved, citation coverage, and reduced senior interruption.

### Feasibility

The MVP is feasible as a local single-repo tool because the required inputs already exist: source files, Git history, optional GitHub metadata, and LLM APIs. The main technical risks are parser coverage, noisy history, and false rationale extraction.

### Risk Controls

- Human verification through citations and raw evidence.
- Conservative claim extraction.
- Graph-first retrieval before vector expansion.
- Explicit missing-evidence states.

---

## References

*   Peng et al., *The Impact of AI on Developer Productivity*: https://arxiv.org/abs/2302.06590
*   Stanford HAI, *Artificial Intelligence Index Report 2025*: https://arxiv.org/abs/2504.07139
*   Google Cloud DORA Reports: https://cloud.google.com/devops/state-of-devops
