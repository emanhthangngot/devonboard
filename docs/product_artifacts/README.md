# DevOnboard Product Artifacts

This directory captures the eight workshop artifacts as bounded product documents. Product artifacts describe user outcomes, decisions, and validation needs. Technical implementation details live in `docs/ARCHITECTURE.md`, `docs/data-model.md`, and `docs/api-spec.json`.

---

## 1. Design Thinking Document

### Empathize

New engineers, maintainers, reviewers, and AI-agent users must reconstruct codebase context from source files, commit history, PRs, issues, stale docs, and senior engineers. They trust concrete evidence more than generic AI prose.

### Define

Engineering teams need a way to answer how, why, and refactor-risk questions with verifiable evidence before they change code.

### Ideate

DevOnboard links current code structure to git/GitHub history and extracted design-rationale claims, then exposes that evidence through cited Q&A, History/Why inspection, benchmark comparison, and evidence packs.

### Riskiest Assumption

Engineers will trust AI onboarding more when the answer exposes both code evidence and historical evidence they can verify quickly.

---

## 2. User Persona

### Primary Persona: New Contributor

- Joins an existing repo and needs a safe first change.
- Searches files, asks AI, reads PRs, and interrupts senior teammates when context is missing.
- Values fast orientation, citations, affected files, and explicit uncertainty.

### Secondary Persona: Maintainer/Reviewer

- Preserves architecture consistency and reviews unfamiliar changes.
- Values rationale history, prior bug/refactor evidence, and copyable context for review.

### Secondary Persona: AI-Agent Power User

- Uses coding agents but needs grounded constraints before allowing code changes.
- Values evidence-only context packs, repo-specific constraints, and exclusion of secrets/private data.

---

## 3. User Journey Map

| Stage | User action | Pain today | DevOnboard outcome |
|---|---|---|---|
| Discover | Receives task or PR | Repo is unfamiliar | Opens prepared repo context |
| Orient | Searches subsystem | Files explain what, not why | Gets structural graph and key nodes |
| Investigate | Reads history | PR/issues are fragmented | Sees History/Why evidence |
| Decide | Plans change or review | AI answers may hallucinate | Gets cited risks and unknowns |
| Share | Reviews or delegates | Context is trapped in one person | Copies cited evidence pack |

---

## 4. DVF Assessment

### Desirability

Strong. Target users already combine grep, GitHub search, `git blame`, PR reading, and teammate questions to solve this problem manually.

### Viability

Credible wedge. DevOnboard uses proprietary repository history and workflow context rather than acting as a thin prompt wrapper.

### Feasibility

Feasible for MVP as a local single-repo demo using source files, Git history, optional GitHub metadata, JSON graph storage, and bounded AI synthesis.

### Risk Controls

- Conservative claim extraction.
- Citations and raw evidence.
- Explicit missing-evidence states.
- Evidence-only mode for private repositories.

---

## 5. Product Roadmap

Use `docs/ROADMAP.md` as the source of truth. It is organized by Now/Next/Later outcomes, not task lists or fixed feature dates.

---

## 6. PRD

Use `docs/spec.md` as the MVP PRD. It defines user stories, acceptance criteria, success criteria, and non-goals. It intentionally avoids database schemas, UI layout commands, and implementation ownership details.

---

## 7. Prototype Plan

Use `docs/PROTOTYPE_PLAN.md` as the source of truth. The prototype validates one flow: load repo context, inspect History/Why evidence, ask a hybrid risk question, verify citations, and copy a bounded evidence pack.

---

## 8. Pitch Deck Outline

1. Problem: code explains what, but not why.
2. User pain: onboarding, review, refactor risk, and AI-agent context are fragmented.
3. Insight: git/GitHub history is institutional memory but is not connected to current code structure.
4. Solution: DevOnboard builds a cited codebase memory graph.
5. Demo: ask how/why/risk questions and inspect raw evidence.
6. Differentiation: graph provenance, conservative claims, evidence packs, benchmarkable trust.
7. Business case: faster onboarding, less senior interruption, safer reviews.
8. MVP proof: five fixed benchmark queries on a pinned demo repo.
