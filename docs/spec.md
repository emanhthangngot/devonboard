# Spec: DevOnboard — AI Codebase Institutional Memory

**Feature ID:** 001-devonboard  
**Status:** Draft  
**Positioning:** Standalone codebase onboarding and institutional-memory system  
**Target demo codebase:** `nextlevelbuilder/goclaw`

---

## Problem Statement

New engineers joining a complex repository face two separate knowledge gaps. They need to understand **how the code works today**, but they also need to understand **why it became that way**. The first answer usually lives in source files, imports, call paths, configs, and tests. The second answer lives in commit messages, pull request descriptions, review comments, issue discussions, and design tradeoffs that are rarely captured in current documentation.

Generic AI coding assistants help with local file reading, but they often miss repository-wide context and historical rationale. Manual onboarding through README files, grep, GitHub search, and asking senior engineers is slow, inconsistent, and hard to verify.

DevOnboard solves this by building a **codebase institutional-memory graph**: a connected representation of code structure, development history, design rationale, authorship, and refactor risk.

---

## Product Thesis

**DevOnboard turns source code and development history into cited institutional memory for engineering teams.**

The product is valuable because it answers questions plain code search cannot:

- How does this subsystem work?
- Why was it designed this way?
- Which commits and PRs explain the decision?
- What alternatives were rejected?
- Who changed it and when?
- Is it safe to refactor this interface?

---

## User Stories

### US-01 — Structural Query

**As** a new contributor,  
**I want to** ask "How does the 8-stage agent pipeline execute a tool call?"  
**So that** I can understand the implementation path without manually tracing dozens of files.

**Acceptance criteria:**
- The answer cites concrete files, functions, or graph nodes.
- The answer includes a concise call/dependency path when available.
- The system distinguishes direct evidence from inferred architecture summaries.
- If structural context is missing, the system says what repository context is unavailable.

### US-02 — Historical Query

**As** a new contributor,  
**I want to** ask "Why was progressive memory loading chosen?"  
**So that** I can understand design intent before changing the memory subsystem.

**Acceptance criteria:**
- The answer cites commits, PRs, review comments, issues, or extracted design claims.
- The answer separates "what the code does" from "why it was built that way".
- If no historical evidence exists, that absence is explicit.
- The answer does not invent rationale from code shape alone.

### US-03 — Hybrid Refactor-Risk Query

**As** a maintainer,  
**I want to** ask "Is it safe to refactor ProviderAdapter?"  
**So that** I can combine dependency impact with past changes, bugs, reviews, and rejected alternatives.

**Acceptance criteria:**
- The structural section lists affected files/functions/modules.
- The historical section surfaces relevant commits, PRs, issues, and claims.
- The answer labels risks and unknowns separately.
- The response gives actionable next inspection steps with citations.

### US-04 — History/Why Panel

**As** a demo viewer or engineer,  
**I want to** click a file/function/module node and see its History/Why context  
**So that** I can inspect evidence without writing a long prompt.

**Acceptance criteria:**
- The panel shows linked commits, PRs, issues, claims, and authors.
- Claims are traceable back to source evidence.
- Nodes with no linked history show a clear empty state.
- Evidence links are clickable where URLs exist.

### US-05 — Ingest Pipeline

**As** a system operator,  
**I want to** refresh the repository context on demand  
**So that** answers reflect the current code and recent development history.

**Acceptance criteria:**
- The user can see when repository context was last refreshed.
- Refreshing context does not create duplicate evidence in future answers.
- The system reports partial refreshes clearly when code or history sources are unavailable.
- The user can exclude noisy generated, vendor, or build artifacts from the context.

### US-06 — Benchmark Dashboard

**As** a workshop attendee,  
**I want to** compare DevOnboard against a plain AI answer  
**So that** the value of graph-grounded context is visible.

**Acceptance criteria:**
- Benchmark uses the same query set across modes.
- Metrics include time-to-useful-answer, citation coverage, evidence usefulness, and human quality score.
- Results are preserved so demo reviewers can compare runs.
- The benchmark explains whether DevOnboard improved trust and verification, not just speed.

### US-07 — PR Review Preparation

**As** a reviewer,  
**I want to** generate a cited evidence pack for unfamiliar files in a pull request  
**So that** I can review with historical context before commenting.

**Acceptance criteria:**
- The evidence pack lists touched files or nodes, linked history, extracted claims, risks, and unknowns.
- The pack can be copied for PR review or team discussion.
- Missing GitHub metadata or private-source limitations are shown explicitly.
- The pack does not claim review safety without cited evidence.

### US-08 — AI-Agent Context Pack

**As** an engineer using a coding agent,  
**I want to** export grounded repo context and constraints  
**So that** the agent does not rely only on local snippets or unsupported assumptions.

**Acceptance criteria:**
- The export includes relevant structural evidence, historical evidence, constraints, and citations.
- The export excludes secrets, generated/vendor files, and unsupported rationale.
- Private-repo exports require explicit external-LLM opt-in or evidence-only mode.
- The export labels stale or partial graph context.

---

## Success Criteria

- DevOnboard reads as a standalone product with its own graph, retrieval, UI, and benchmark.
- The core demo can answer one structural, one historical, and one hybrid question with citations.
- The demo can produce one PR review evidence pack and one AI-agent context pack.
- The graph is inspectable as JSON and can be rebuilt from repo + git/GitHub data.
- Product artifacts outside `docs/` align with this same problem and product story.

---

## Non-Goals

- Not a generic chatbot.
- Not a GitHub clone.
- Not a production multi-tenant SaaS for MVP.
- Not a replacement for human code review.
- Not an autonomous code-changing agent.
- Not a tool that uploads private source code to third-party LLMs by default.
