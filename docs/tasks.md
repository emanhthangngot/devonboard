# Tasks: DevOnboard Standalone MVP

---

## Phase 1 — Documentation

- [ ] Rewrite all `docs/*.md` around standalone DevOnboard.
- [ ] Update `00_problem_statement.md`.
- [ ] Update `01_market_and_domain/`.
- [ ] Update `02_theme_deep_dive/`.
- [ ] Update `03_target_users/`.
- [ ] Update `04_case_studies/`.
- [ ] Update `05_use_cases/`.
- [ ] Add `docs/PROTOTYPE_PLAN.md`, `docs/ROADMAP.md`, and `docs/ARTIFACT_ALIGNMENT.md`.
- [ ] Add defensive UX and human-verification requirements.
- [ ] Audit all Markdown files for unresolved template residue and stale positioning.

**Checkpoint:** no public Markdown file frames DevOnboard as dependent on another project.

---

## Phase 2 — Graph Core

- [ ] Define graph models.
- [ ] Implement deterministic ID helpers.
- [ ] Implement JSON graph store.
- [ ] Implement upsert/merge logic.
- [ ] Test idempotent merge behavior.

**Checkpoint:** graph can be created, saved, loaded, and updated without duplicate nodes.

---

## Phase 3 — Structure Scanner

- [ ] Implement file inventory with ignore patterns.
- [ ] Extract supported symbols and imports.
- [ ] Create structural nodes and edges.
- [ ] Add file/module summaries.

**Checkpoint:** `devonboard scan --repo target_repo` creates a usable structural graph.

---

## Phase 4 — History Ingest

- [ ] Extract commit metadata and touched files.
- [ ] Fetch PR/issue/review metadata.
- [ ] Create source/entity nodes.
- [ ] Link sources to files/functions/modules.

**Checkpoint:** selected file nodes show linked commits/PRs.

---

## Phase 5 — Claims And Retrieval

- [ ] Extract explicit rationale claims.
- [ ] Link claims to sources.
- [ ] Implement structural retrieval.
- [ ] Implement historical retrieval.
- [ ] Implement hybrid retrieval.

**Checkpoint:** structural, historical, and hybrid test queries return evidence lists.

---

## Phase 6 — API, UI, Benchmark

- [ ] Add scan, ingest, query, graph, and benchmark endpoints.
- [ ] Build workspace UI.
- [ ] Build History/Why inspector.
- [ ] Build benchmark dashboard.
- [ ] Add quickstart and demo script.

**Checkpoint:** full demo runs locally with cited answers and benchmark output.
