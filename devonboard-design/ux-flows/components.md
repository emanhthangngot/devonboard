# components.md — Behavioral Component Specs (ux-flows)

> Behavior contracts. Pair with `design-systems/devonboard-default/components.md`
> for visual styling and `states.md` for required states.

---

## 1. TopNav

**Responsibilities:**
- Show current repo name, branch, and pinned commit (`TARGET_REPO_COMMIT`).
- Show live scan status (idle / scanning / done / error) and ingest status
  (idle / ingesting / done / error) as independent pills.
- Provide a link/tab to the Benchmark view.

**Behavior:**
- Clicking the scan/ingest pill while in "error" state opens a small popover with
  the error detail and a "Retry" button.
- Status pills poll or subscribe to backend status; do not require manual refresh.

---

## 2. GraphPane (Left Panel)

**Responsibilities:**
- List files/directories (Files view) or domain/module/service groupings (Graph view).
- Support selection of any node type defined in `data-model.md` §2.
- Support text filter/search across node names and file paths.

**Behavior:**
- Selecting a node updates the right panel (History/Why) without affecting the
  center Q&A thread.
- Nodes referenced by a citation in the center panel are highlighted in this panel
  when that citation is clicked (scroll into view + temporary highlight flash).
- View toggle (Files/Graph) persists per session (not per node selection).

---

## 3. QueryPanel (Center)

**Responsibilities:**
- Mode selector: `auto | structural | historical | hybrid` (maps to `QueryRequest.mode`).
- Multiline query input with submit (Enter to submit, Shift+Enter for newline).
- Render Q&A thread: each turn = user query + answer + citations + controls.

**Behavior:**
- On submit, immediately show the user query in the thread and a loading indicator
  for the answer (do not wait for the full response to render anything).
- When the `POST /query` response returns, show a small route badge
  (`structural` / `historical` / `hybrid`) next to the answer.
- Hybrid answers render with labeled sections per AI.md §4: "Structural impact",
  "Historical context", "Refactor guidance" — only render sections that have content,
  but if historical evidence was expected and is absent, render the section with the
  explicit "no evidence" message rather than omitting it.
- Inline citation chips (`[1]`, `[2]`, …) map 1:1 to entries in `citations[]`. Clicking
  a chip: (a) scrolls to/highlights the corresponding CitationCard in the right panel,
  (b) if the right panel is showing a different node, switch it to show this citation's
  source context.
- Per-answer controls (always visible, not hidden behind a menu):
  - "Show retrieved context" — expands a collapsible raw-context panel below the answer.
  - "Mark as unsupported / not useful" — opens a 1-line reason input, submits feedback.
  - "Retry with narrower scope" — only shown when `warnings` includes a "too broad" signal.
- Suggested demo queries (idle state) are the 5 queries from AI.md §6, each as a
  clickable chip that populates and submits the query input.

---

## 4. History/Why Inspector (Right Panel)

**Responsibilities:**
- For the selected node, show grouped evidence: Linked Commits/PRs, Claims,
  Authors/Reviewers, Risks/Contradictions (per PROVENANCE_GRAPH.md §4).
- Each group renders as a labeled section containing zero or more CitationCards.

**Behavior:**
- Sections always render, even when empty (show "No X found." per `states.md` §4).
- Claims show their `confidence` value; below a configurable threshold (default 0.6),
  add a "Low confidence" badge and a tooltip with the raw confidence number.
- "Risks/Contradictions" section surfaces edges of type `contradicts` and any claim
  tagged with risk-related tags (`risk`, `breaking-change`, `compatibility`, etc.).
- A "Generate Evidence Pack" button at the panel footer opens the Evidence Pack panel
  (see `layout.md` §4) pre-scoped to the selected node.

---

## 5. CitationCard

**Responsibilities:**
- Represent one `Evidence` item: type, label, summary, optional URL/score.

**Behavior:**
- Clicking the card opens the raw source:
  - `file`/`function`/etc. → scroll/select that node in the left panel.
  - `commit`/`pr`/`issue`/`review` with URL → open URL in new tab.
  - `commit` without URL (no GitHub token) → open local diff view (modal or inline
    expansion showing commit message + changed files).
  - `claim` → expand inline to show full claim summary + linked `source` citations
    (`extractedFrom`).
- Cards excluded from AI context (secrets/generated/vendor) render in muted style
  with an "Excluded from AI context" tag but remain clickable for inspection.

---

## 6. Evidence Pack Panel

**Responsibilities:**
- Generate and display PR-review or AI-agent-context evidence packs
  (`EvidencePack` model in data-model.md §7).

**Behavior:**
- Purpose toggle: "PR Review" vs "AI-Agent Context" — switching re-triggers
  `POST /evidence-packs` with the new `purpose`.
- Markdown preview renders the pack content read-only with citation references
  visually distinguished (same chip style as QueryPanel).
- "Copy" copies raw markdown to clipboard with a brief confirmation toast
  ("Copied to clipboard").
- "Export" downloads the markdown as a `.md` file.
- Warnings and `excluded_sources` always render above the action buttons, never
  hidden in a collapsed section — per constitution.md Q1 (citation completeness)
  and FRONTEND.md §7.

---

## 7. BenchmarkPanel

**Responsibilities:**
- Run and display benchmark comparisons (`BenchmarkRun` / `MetricRow` models).

**Behavior:**
- "Run Benchmark" calls `POST /benchmark` and runs the fixed 5-query set (AI.md §6) in both `devonboard` and
  `plain_agent` modes.
- Comparison table: one row per query, columns grouped by mode (devonboard |
  plain_agent), metrics = time-to-useful-answer, citations count, evidence count,
  evidence usefulness score, human quality score.
- Charts (bar or grouped-bar) visualize time-to-useful-answer and citation count
  per query, comparing both modes side by side.
- Past runs are listed with timestamp + repo/commit; selecting a past run replaces
  the displayed table/charts (does not navigate away).
- Human quality score and evidence usefulness score are editable inline (manual
  rating input, 1–5) since they require human judgment per `data-model.md` §8.

---

## 8. Setup / No-Repo State

**Responsibilities:**
- Guide the user to configure `TARGET_REPO_PATH` and run an initial scan.

**Behavior:**
- Single card in center panel: repo path display (from env, read-only in MVP),
  "Run Scan" button, link to quickstart steps.
- After scan completes, the card is replaced by the normal workspace — no separate
  navigation/redirect needed.
