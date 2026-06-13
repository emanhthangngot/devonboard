# Quickstart: DevOnboard

---

## Prerequisites

```bash
git --version
python --version
node --version
docker --version   # optional, for Qdrant
```

---

## Setup

```bash
git clone <this-repo> devonboard
cd devonboard
cp .env.example .env
```

Fill `.env`:

```bash
TARGET_REPO_PATH=./target_repo
DEVONBOARD_GRAPH_PATH=./devonboard/knowledge-graph.json
GITHUB_TOKEN=...
GEMINI_API_KEY=...
MAX_COMMITS_INGEST=500
TARGET_REPO_BRANCH=dev
TARGET_REPO_COMMIT=<pin-for-demo>
ALLOW_EXTERNAL_LLM_FOR_PRIVATE_REPO=false
```

Clone target repo:

```bash
git clone https://github.com/nextlevelbuilder/goclaw target_repo
```

---

## Build Graph

```bash
devonboard scan --repo target_repo
devonboard ingest-history --repo target_repo --max-commits 500
```

Expected output:

```text
devonboard/knowledge-graph.json
```

---

## Run App

```bash
make up
```

Open:

```text
http://localhost:3000
```

---

## Demo Queries

```text
How does the agent pipeline execute a tool call?
Why was progressive memory loading chosen?
Is it safe to refactor ProviderAdapter?
What should I inspect before reviewing changes touching ProviderAdapter?
Create a cited context pack for an agent modifying the provider subsystem.
```

---

## Benchmark

```bash
devonboard benchmark
```

Expected result:

```text
benchmark/results/<timestamp>.json
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No graph found | run `devonboard scan` |
| No history evidence | run `devonboard ingest-history` |
| GitHub rate limit | reduce `MAX_COMMITS_INGEST` or add token |
| LLM unavailable | inspect retrieved evidence directly |
| Private repo with external LLM disabled | use evidence-only context and citations |
| Generated/vendor files skipped | review `EXCLUDE_PATTERNS` before scan |
