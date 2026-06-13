# DevOnboard

**AI codebase onboarding with cited institutional memory.**

DevOnboard scans a repository, ingests development history, extracts design rationale, and builds a knowledge graph that answers how the code works, why it was designed that way, and what risks matter before refactoring.

---

## What It Does

- Builds a structural graph of files, functions, modules, services, and flows.
- Links code artifacts to commits, PRs, review comments, issues, and authors.
- Extracts design-rationale claims from historical evidence.
- Answers structural, historical, and hybrid questions with citations.
- Provides a History/Why inspector for selected code nodes.
- Benchmarks DevOnboard against a plain AI answer.

---

## Quick Start

```bash
cp .env.example .env
git clone https://github.com/nextlevelbuilder/goclaw target_repo
make up
```

Open `http://localhost:3000`, then use the workspace controls to run Scan and Ingest History.

---

## Core Artifact

```text
devonboard/knowledge-graph.json
```

This graph is the durable memory layer. Optional indexes can be rebuilt from it.

## MVP Interface

DevOnboard MVP is a local web app backed by FastAPI. Scan, ingest, query, evidence-pack generation, and benchmark runs are triggered from the web workspace. A public CLI is out of scope for MVP and may be added later as a thin API wrapper.

---

## Pitch

DevOnboard turns code structure and development history into cited institutional memory, so engineers can onboard faster and make safer changes.
