# Frontend — DevOnboard Workspace UI

---

## 1. UX Principle

The app opens directly into the working product. No marketing landing page.

Primary user task:

```text
select or confirm local repo context -> scan/ingest -> inspect graph/history -> ask cited questions
```

---

## 2. Layout

```text
TopNav
  repo name/path or GitHub URL, branch/commit, scan status, ingest status, result link

Main Workspace
  Left: graph/file/subsystem navigation
  Center: Q&A thread and cited answer
  Right: History/Why inspector

Result View
  query set, run button, app metric table, charts
```

---

## 3. Core Components

- `RepoContextPanel`: local target repo path or public GitHub URL input, branch/commit display, and scan trigger.
- `GraphPane`: visual or list-based graph explorer.
- `NodeInspector`: selected node overview.
- `HistoryPanel`: commits, PRs, issues, claims, authors.
- `QueryPanel`: mode selector, input, answer, citations, and retrieved context.
- `CitationCard`: file, commit, PR, issue, claim evidence.
- `ResultPanel`: stored app result runs.
- `EvidencePackPanel`: copyable PR review and AI-agent context packs.

---

## 4. History/Why Inspector

For a selected node, show:

- linked source evidence;
- design claims;
- authors/reviewers;
- related risks;
- missing-evidence empty state.

Evidence should be compact, clickable, and grouped by type.

---

## 5. Visual Style

- Dense, engineer-native layout.
- Light theme for projector readability.
- Small cards, clear tables, compact typography.
- Distinct badges:
  - structural: blue;
  - historical source: green;
  - claim: amber;
  - risk/contradiction: red.

---

## 6. Required States

- No repo loaded.
- Repo path configured but graph missing.
- Scan running.
- History ingest running.
- Query running.
- Selected node with no history.
- Selected node with multiple evidence types.
- Result running.
- API or token error.

---

## 7. Repo Context Switching

Repo switching accepts either a local path or a public GitHub HTTPS URL. The
frontend stores the last value in browser-local state and sends that same value
to scan and history ingest operations.

- `POST /scan` receives the selected `repo_path`, `branch`, and optional `commit`.
- For GitHub URLs, the backend clones/fetches into the managed ignored cache
  configured by `DEVONBOARD_REPO_CACHE_PATH`.
- `POST /ingest/history` receives the same selected `repo_path` so history ingest
  cannot accidentally read the old `TARGET_REPO_PATH`.
- The UI does not write `.env`.
- Health/status UI may show non-secret repo context, but must never render tokens
  or provider credentials.

---

## 8. Defensive UX / Human Verification

DevOnboard must behave like a copilot, not an autopilot. The UI should help the user verify or reject AI output.

Required controls:

- Open raw source evidence for any citation.
- Show retrieved context behind an answer.
- Mark an answer as unsupported or not useful.
- Retry with a narrower scope when a query is too broad.
- Copy an evidence pack for PR review or team discussion.
- Export evidence-only context for coding agents without secrets or unsupported rationale.

Required warning states:

- Insufficient evidence for rationale.
- Low-confidence claim extraction.
- Stale graph or partial ingest.
- History unavailable because GitHub metadata could not be fetched.
- Answer includes inferred structure but no direct historical rationale.
- External LLM disabled because repository data is private and opt-in was not granted.
