# states.md — Required UI States Matrix

> Every component below MUST implement every listed state. A PR/build that ships a
> component missing a required state is incomplete (FRONTEND.md §6–7,
> ARCHITECTURE.md §7).

---

## 1. App-Level States

| State | Trigger | UI |
|---|---|---|
| No repo loaded | Fresh install / no `TARGET_REPO_PATH` configured | Center panel shows setup card: "Configure target repo" with path input + clone instructions. Left/right panels show empty placeholders. |
| Scanning | `POST /scan` in progress | TopNav scan pill = "Scanning…" (animated dot). Left panel shows skeleton tree rows. |
| Ingesting history | `POST /ingest/history` in progress | TopNav ingest pill = "Ingesting history…". Right panel shows skeleton CitationCards if a node is selected. |
| Graph missing | No `knowledge-graph.json` found | Center panel empty state: "No graph found. Run a scan to get started." + button. |
| API/token error | Backend returns 4xx/5xx or GitHub token invalid | Top-of-panel banner (`--color-error`), specific message (e.g. "GitHub token invalid — commit-only ingest will be used"). Non-blocking. |

---

## 2. QueryPanel (Center) States

| State | Trigger | UI |
|---|---|---|
| Idle / empty thread | No queries yet | Show 3–5 suggested demo queries (clickable, from AI.md benchmark set) as chips/list. |
| Query streaming | `GET /query/stream` active | Answer text streams progressively with trailing cursor indicator. Mode/route badge appears as soon as route is known (don't wait for full answer). |
| Answer with citations | Stream complete, citations present | Citations rendered as inline chips + linked to right panel CitationCards. "Mark unsupported" and "Open raw evidence" controls visible. |
| Answer with no historical evidence | Historical route/section empty | Explicit line: "No historical evidence found for this query." — never omit the section silently. |
| Query too broad | Backend signals broad/ambiguous query | Show clarification prompt + "top subsystems" suggestions with caveat text, plus a "Retry with narrower scope" action. |
| Low-confidence claim | `confidence` below threshold on a claim | Claim renders with `--color-warning` badge "Low confidence" + tooltip explaining why. |
| LLM unavailable | Synthesis fails but evidence retrieved | Show retrieved evidence list directly (structural + historical), with banner: "Answer synthesis unavailable — showing retrieved evidence." |
| External LLM disabled (private repo) | `ALLOW_EXTERNAL_LLM_FOR_PRIVATE_REPO=false` and repo marked private | Banner: "External LLM disabled for this repository. Showing evidence-only results." Query still returns evidence list, no synthesized prose. |

---

## 3. GraphPane / Left Nav States

| State | Trigger | UI |
|---|---|---|
| Empty (no scan yet) | Graph has zero nodes | Placeholder: "Run a scan to populate the file/graph navigator." |
| Populated | Nodes exist | Tree/list rendered, grouped by directory (Files view) or domain/module (Graph view). |
| Symbol extraction failed for a file | Parser fallback to file-level | File node shows a small "file-level only" indicator icon (tooltip: "Detailed symbols unavailable for this file type"). |
| Search/filter active | User types in nav filter | Non-matching rows hidden, match count shown in panel header. |

---

## 4. History/Why Inspector (Right Panel) States

| State | Trigger | UI |
|---|---|---|
| No node selected | Default | Placeholder: "Select a file, function, or module to see its History/Why context." |
| Node selected, no history | Node has zero linked `source`/`claim` edges | Per section ("Linked Commits/PRs", "Claims", "Risks"): show "No linked commits/PRs found." etc. — each section stays visible. |
| Node selected, full evidence | Node has commits/PRs/claims/authors | All sections populated with CitationCards, grouped and labeled by type. |
| History unavailable (GitHub) | `GITHUB_TOKEN` missing or API unreachable | Banner at top of panel: "GitHub metadata unavailable — showing commit-only history." Commit-derived sections still populate. |
| Stale graph | Graph `generated_at` older than configured threshold or partial ingest flag set | Persistent banner (`--color-warning`): "Graph may be stale — last updated {date}. Re-run scan/ingest for current data." |

---

## 5. CitationCard States

| State | Trigger | UI |
|---|---|---|
| Default | Evidence has URL + summary | Full card: badge, title, summary, metadata, clickable to open raw source. |
| No URL available | Local-only commit, no GitHub metadata | Card still clickable — opens local diff/commit view instead of external link. No broken link icons. |
| Excluded from AI context | Source matched secret/generated/vendor pattern | Card shows muted style with "Excluded from AI context" tag (`--color-text-faint`), still viewable but visually de-emphasized. |

---

## 6. Evidence Pack Panel States

| State | Trigger | UI |
|---|---|---|
| Generating | `POST /evidence-packs` in progress | Skeleton markdown blocks + disabled Copy/Export buttons. |
| Generated, clean | No warnings/exclusions | Markdown preview + citations list + enabled Copy/Export. |
| Generated with warnings | `warnings[]` non-empty | Warnings section visible above Copy/Export (`--color-warning` banners), e.g. "3 sources excluded (generated files)." |
| Private repo, no opt-in | `ALLOW_EXTERNAL_LLM_FOR_PRIVATE_REPO=false` | Pack generated in evidence-only mode; banner: "Generated without external LLM — evidence-only export." |

---

## 7. Benchmark View States

| State | Trigger | UI |
|---|---|---|
| No runs yet | `benchmark_runs` empty | Empty state: "Run a benchmark to compare DevOnboard with a plain-agent answer." + Run button. |
| Running | `POST /benchmark/run` in progress | Per-query progress rows (devonboard / plain_agent), spinner per cell being computed. |
| Completed | Results stored | Comparison table fully populated + charts rendered. |
| Run failed (partial) | Some queries errored | Failed rows show `--color-error` cell with retry icon; completed rows still shown. |

---

## 8. Cross-Cutting Rules

- Every async action (scan, ingest, query, benchmark, evidence pack) must show a
  state within 300ms of user action — never a frozen UI with no feedback.
- Every "empty" state must include a next-step action when one exists (button/link),
  not just descriptive text.
- Warning/error banners are dismissible but must reappear if the underlying condition
  persists across a page reload.
