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

- [x] Define graph models.
- [x] Implement deterministic ID helpers.
- [x] Implement JSON graph store.
- [x] Implement upsert/merge logic.
- [x] Test idempotent merge behavior.

**Checkpoint:** graph can be created, saved, loaded, and updated without duplicate nodes.

---

## Phase 3 — Structure Scanner

- [x] Implement file inventory with ignore patterns.
- [x] Extract supported symbols and imports.
- [x] Create structural nodes and edges.
- [x] Add file/module summaries.

**Checkpoint:** The web workspace **Run Scan** action calls `POST /scan` and creates a usable structural graph.

---

## Phase 4 — History Ingest

- [x] Extract commit metadata and touched files.
- [ ] Fetch PR/issue/review metadata.
- [x] Create source/entity nodes.
- [x] Link sources to files/functions/modules.

**Checkpoint:** selected file nodes show linked commits/PRs.

---

## Phase 5 — Claims And Retrieval

- [x] Extract explicit rationale claims.
- [x] Link claims to sources.
- [x] Implement structural retrieval.
- [x] Implement historical retrieval.
- [x] Implement hybrid retrieval.

**Checkpoint:** structural, historical, and hybrid test queries return evidence lists.

---

## Phase 6 — API, UI, Benchmark

- [x] Add scan, ingest, query, graph, and benchmark endpoints.
- [x] Build workspace UI.
- [x] Build History/Why inspector.
- [x] Build benchmark dashboard.
- [x] Add quickstart and demo script.

**Checkpoint:** full web demo runs locally with cited answers, evidence packs, and benchmark output.

---

## Implementation Status

- [x] Root `Makefile` runs backend tests, frontend tests, build, and E2E smoke.
- [x] FastAPI backend exposes health, scan, ingest, graph, query, evidence-pack, and benchmark routes.
- [x] Next.js frontend provides a Claude-style workspace and benchmark dashboard.
- [x] E2E smoke covers scan, history ingest, cited query, evidence pack, and benchmark.
- [ ] GitHub PR, issue, and review metadata enrichment remains a follow-up beyond local Git history ingest.
- [ ] Full documentation rewrite in Phase 1 remains a separate content pass.
