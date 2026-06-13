# Frontend — DevOnboard Workspace UI

---

## 1. UX Principle

The app opens directly into the working product. No marketing landing page.

Primary user task:

```text
select repo context -> inspect graph/history -> ask cited questions
```

---

## 2. Layout

```text
TopNav
  repo name, scan status, ingest status, benchmark link

Main Workspace
  Left: graph/file/subsystem navigation
  Center: Q&A thread and streamed answer
  Right: History/Why inspector

Benchmark View
  query set, run button, comparison table, charts
```

---

## 3. Core Components

- `GraphPane`: visual or list-based graph explorer.
- `NodeInspector`: selected node overview.
- `HistoryPanel`: commits, PRs, issues, claims, authors.
- `QueryPanel`: mode selector, input, streamed answer.
- `CitationCard`: file, commit, PR, issue, claim evidence.
- `BenchmarkPanel`: stored benchmark runs.

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
- Scan running.
- History ingest running.
- Query streaming.
- Selected node with no history.
- Selected node with multiple evidence types.
- Benchmark running.
- API or token error.

---

## 7. Defensive UX / Human Verification

DevOnboard must behave like a copilot, not an autopilot. The UI should help the user verify or reject AI output.

Required controls:

- Open raw source evidence for any citation.
- Show retrieved context behind an answer.
- Mark an answer as unsupported or not useful.
- Retry with a narrower scope when a query is too broad.
- Copy an evidence pack for PR review or team discussion.

Required warning states:

- Insufficient evidence for rationale.
- Low-confidence claim extraction.
- Stale graph or partial ingest.
- History unavailable because GitHub metadata could not be fetched.
- Answer includes inferred structure but no direct historical rationale.
