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
TARGET_REPO_BRANCH=dev
TARGET_REPO_COMMIT=<pin-for-demo>
MAX_COMMITS_INGEST=500
ALLOW_EXTERNAL_LLM_FOR_PRIVATE_REPO=false
```

Clone target repo:

```bash
git clone https://github.com/nextlevelbuilder/goclaw target_repo
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

Run the verification suite:

```bash
make test
make e2e
```

---

## Build Graph From The Web UI

Use the workspace controls:

1. Click **Run Scan**.
2. Wait for scan status to become `done`.
3. Click **Ingest History**.
4. Wait for ingest status to become `done` or `partial`.

Expected output:

```text
devonboard/knowledge-graph.json
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

Open the Benchmark view and click **Run Benchmark**.

Expected result:

```text
benchmark/results/<timestamp>.json
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No graph found | click **Run Scan** in the web workspace |
| No history evidence | click **Ingest History** in the web workspace |
| GitHub rate limit | reduce `MAX_COMMITS_INGEST` or add token |
| LLM unavailable | inspect retrieved evidence directly |
| Private repo with external LLM disabled | use evidence-only context and citations |
| Generated/vendor files skipped | review `EXCLUDE_PATTERNS` before scan |
