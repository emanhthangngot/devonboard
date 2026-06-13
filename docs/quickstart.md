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
