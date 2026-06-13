# Plan: DevOnboard Standalone MVP

**Feature ID:** 001-devonboard  
**Stack:** FastAPI + Next.js + Git/GitHub ingest + JSON graph + optional Qdrant/Gemini

This is an engineering execution plan, not the product roadmap. Product themes and time horizons live in `docs/ROADMAP.md`.

---

## Overview

Build DevOnboard as a standalone local web app that scans a target repository, ingests git/GitHub history, extracts design-rationale claims, builds `devonboard/knowledge-graph.json`, and answers structural, historical, and hybrid onboarding questions with citations.

---

## Architecture Decisions

- Store the durable graph as JSON so it is inspectable and easy to demo.
- Keep Qdrant optional; graph traversal must work without it.
- Use conservative rationale extraction to avoid false design claims.
- Use a single-repo MVP to keep setup and demo reliable.
- Treat benchmark output as product evidence, not a later bolt-on.

---

## Phase 1 — Documentation Reset

- Rewrite all technical docs to describe DevOnboard as a standalone product.
- Replace external-integration language with product-native graph/provenance terminology.
- Align context pack files from `00_problem_statement.md` through `05_use_cases/`.
- Add dedicated prototype, roadmap, and artifact-alignment documents.
- Audit every Markdown file for unresolved template residue, stale positioning, and artifact-boundary violations.

---

## Phase 2 — Graph Foundation

- Implement graph node/edge models and deterministic ID helpers.
- Implement graph merge/idempotency rules.
- Implement JSON graph persistence at `devonboard/knowledge-graph.json`.
- Add tests for duplicate-safe node/edge upsert.

---

## Phase 3 — Structure Scanner

- Inventory files and directories with ignore rules.
- Extract functions/classes/imports for supported languages.
- Create `file`, `function`, `module`, `config`, and dependency edges.
- Add fallback file-level summaries for unsupported files.

---

## Phase 4 — History Ingest

- Extract commits, authors, dates, messages, bodies, and touched files.
- Fetch PR, review, and issue metadata when `GITHUB_TOKEN` is available.
- Create `source` and `entity` nodes.
- Link source nodes to structural nodes using touched files.

---

## Phase 5 — Rationale Extraction

- Run structured extraction over PR/commit/review text.
- Create `claim` nodes only from explicit rationale.
- Link claims to source evidence.
- Add `builds_on` and `contradicts` edges only when supported by text.

---

## Phase 6 — Query And Synthesis

- Implement query classification.
- Implement structural, historical, and hybrid retrieval.
- Assemble grounded context windows.
- Stream answers with citations via SSE.

---

## Phase 7 — Frontend And Benchmark

- Build workspace UI with graph/file navigation, Q&A panel, and History/Why inspector.
- Build benchmark dashboard with stored JSON runs.
- Add suggested demo queries.
- Validate full demo from clean setup.

---

## Verification

- `scan` creates structural graph nodes for the target repo.
- `ingest-history` adds historical evidence without duplicates.
- A selected file/function shows History/Why evidence.
- The three canonical query types return cited answers.
- Benchmark produces comparable rows for DevOnboard and plain-agent modes.
