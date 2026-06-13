# layout.md — Screen & Panel Structure

> Derived from FRONTEND.md §1–2 and ARCHITECTURE.md §4.

---

## 1. Core UX Principle

The app opens directly into the working workspace. **No marketing landing page, no
onboarding wizard, no auth screen for MVP.** The primary task is:

```text
select repo context -> inspect graph/history -> ask cited questions
```

---

## 2. App Shell

```text
┌──────────────────────────────────────────────────────────────────┐
│ TopNav  [repo name | branch/commit] [scan status] [ingest status] │
│                                            [Benchmark tab/link]    │
├───────────────┬──────────────────────────────┬────────────────────┤
│ Left Panel     │ Center Panel                  │ Right Panel        │
│ GraphPane /    │ QueryPanel                     │ History/Why        │
│ File/Subsystem │ - mode selector                │ Inspector          │
│ Navigation     │ - Q&A thread                   │ - linked sources   │
│                │ - answer + citations            │ - claims           │
│                │                                 │ - authors/reviewers│
│                │                                 │ - risks            │
└───────────────┴──────────────────────────────┴────────────────────┘
```

- Left panel width: `--panel-left-width` (240px), resizable, collapsible to icon rail.
- Right panel width: `--panel-right-width` (320px), resizable, collapsible to icon rail.
- Center panel: flexible, minimum `--panel-min-center` (480px).
- On narrow viewports (<1024px): right panel becomes an overlay/drawer triggered from
  the selected node; left panel collapses to rail by default.

---

## 3. Benchmark View

Separate tab/route, not a modal. Layout:

```text
┌──────────────────────────────────────────────────────────────────┐
│ TopNav (same)                                                      │
├──────────────────────────────────────────────────────────────────┤
│ Query set selector + "Run Benchmark" button                       │
├──────────────────────────────────────────────────────────────────┤
│ Comparison table: DevOnboard vs plain-agent (per query row)       │
├──────────────────────────────────────────────────────────────────┤
│ Charts: time-to-useful-answer, citation count, evidence count     │
├──────────────────────────────────────────────────────────────────┤
│ Stored run history (selectable past runs)                         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Evidence Pack Panel

Rendered as a slide-over panel from the right side (overlaying or replacing the
History/Why inspector), triggered from a node, a query result, or a dedicated
"Generate Evidence Pack" action.

```text
┌────────────────────────────┐
│ Evidence Pack — [purpose]   │
│ [PR Review | AI-Agent Ctx]  │
├────────────────────────────┤
│ Markdown preview (scroll)   │
├────────────────────────────┤
│ Citations list               │
├────────────────────────────┤
│ Warnings / excluded sources  │
├────────────────────────────┤
│ [Copy] [Export]              │
└────────────────────────────┘
```

---

## 5. Navigation Model

- Left panel supports two view modes, switchable via small tabs at panel top:
  **Files** (tree view by path) and **Graph** (subsystem/domain grouping by node type).
- Selecting any node (file, function, module, service, domain, flow) updates:
  1. Center panel — does NOT change (Q&A thread persists across selections).
  2. Right panel — updates to show that node's History/Why context.
- Clicking a citation in the center panel selects the corresponding node in the left
  panel and updates the right panel (cross-panel sync is required).

---

## 6. Responsive Rules

| Breakpoint | Left Panel | Center | Right Panel |
|---|---|---|---|
| ≥1280px | full (240px) | flexible | full (320px) |
| 1024–1279px | rail (48px) | flexible | full (320px) |
| <1024px | rail, drawer on tap | full width | drawer/overlay on node select |

Benchmark tables degrade to horizontally scrollable on narrow viewports — never
wrap numeric columns.
