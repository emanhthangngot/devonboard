# components.md — Visual Component Styling (devonboard-default)

> Visual rules only. For behavior/required states, see `ux-flows/components.md` and
> `ux-flows/states.md`.

---

## 1. TopNav

- Height: `--topnav-height`, background `--color-bg`, bottom border `--color-border`.
- Left: repo name (mono, `--text-sm`) + branch/commit pill.
- Center/right: scan status pill, ingest status pill, "Benchmark" link/tab.
- Status pills use `--badge-height`, rounded `--radius-sm`, colored per status
  (`--color-success` / `--color-warning` / `--color-error` backgrounds at 10% opacity).

---

## 2. Left Panel — GraphPane / File Nav

- Background `--color-bg-subtle`, right border `--color-border`.
- Tree rows: `--row-height-compact`, mono font for file paths (`--text-xs`),
  sans for folder/module labels (`--text-sm`).
- Active/selected row: `--color-primary-subtle` background, left border 2px
  `--color-primary`.
- Hover row: `--color-bg-muted`.
- Node type icons (file/function/class/module/etc.) at 14px, `--color-text-muted`.
- Collapsed state: render as `--rail-collapsed-width` icon-only rail with tooltip labels.

---

## 3. Center Panel — QueryPanel / Q&A Thread

- Background `--color-bg`.
- Each Q&A turn is a block separated by `--space-4` vertical gap, no card border
  (avoid nested-card fatigue in a long thread).
- User query: `--text-base`, `--color-text`, `500` weight, left-aligned, no bubble.
- Mode selector (auto/structural/historical/hybrid): segmented control, `--button-height`,
  `--radius-sm`, active segment `--color-primary-subtle` background.
- Streamed answer body: `--text-base`, `--color-text`, line-height 1.6.
- Section headers inside hybrid answers ("Structural impact", "Historical context",
  "Refactor guidance"): `--text-sm`, `600` weight, `--color-text-muted`, uppercase,
  letter-spacing 0.04em, `--space-2` top margin.
- Inline citation markers: superscript-style chip, `--text-xs`, `--color-primary`,
  `--color-primary-subtle` background, `--radius-sm`, clickable.

---

## 4. Right Panel — History/Why Inspector

- Background `--color-bg`, left border `--color-border`.
- Header: selected node name (mono, `--text-sm`) + node type badge.
- Sections: "Linked Commits/PRs", "Claims", "Authors/Reviewers", "Risks". Each section
  has a `--text-xs` uppercase label (`--color-text-muted`) and a list of CitationCards.
- Empty section: single-line muted text, e.g. "No linked commits found." — never
  hide the section entirely (FRONTEND.md §6 empty states).

---

## 5. CitationCard

- Compact card: `--radius-sm`, 1px `--color-border`, padding `--space-2`,
  `--row-height-default` minimum height, `--space-2` gap between stacked cards.
- Layout: type badge (left) + title/summary (`--text-sm`, 1–2 lines, truncate with
  ellipsis) + metadata row (`--text-xs`, `--color-text-muted`: author, date, score).
- Type badge colors map directly to evidence type:
  - `file`/`function`/`module`/etc. → `--color-structural-bg` / `--color-structural`
  - `commit`/`pr`/`issue`/`review` → `--color-historical-bg` / `--color-historical`
  - `claim` → `--color-claim-bg` / `--color-claim`
  - risk/contradiction → `--color-risk-bg` / `--color-risk`
- Hover: `--shadow-sm`, border becomes `--color-border-strong`.
- Click target: entire card opens raw source evidence (per FRONTEND.md §7 requirement).

---

## 6. Badges

- Height `--badge-height`, padding `0 6px`, `--radius-sm`, `--text-xs`, `500` weight.
- Always paired background+text color from the semantic palette in `tokens.md` §1.3 —
  never gray badges for evidence types (gray is reserved for neutral metadata only).

---

## 7. Buttons

- Default height `--button-height`, `--radius-sm`, `--text-sm`, `500` weight.
- **Primary**: `--color-primary` background, white text, `--color-primary-hover` on hover.
- **Secondary**: `--color-bg`, 1px `--color-border`, `--color-text`; hover
  `--color-bg-muted`.
- **Destructive/Warning actions** (e.g. "Mark unsupported"): outline style using
  `--color-risk` / `--color-warning` border + text, transparent background.
- Icon-only buttons (copy, retry, dismiss): 28x28px, `--radius-sm`, `--color-text-muted`,
  hover `--color-bg-muted` + `--color-text`.

---

## 8. Forms & Inputs

- Height `--row-height-default`, `--radius-sm`, 1px `--color-border`, focus ring
  2px `--color-primary` at 30% opacity + `--color-border-strong` border.
- Placeholder text `--color-text-faint`.
- Query input (center panel): multiline, auto-grow up to 6 lines, mono font when
  content looks like a file path/identifier, otherwise sans.

---

## 9. Tables (Benchmark, Graph lists)

- Header row: `--color-bg-subtle` background, `--text-xs` uppercase `--color-text-muted`,
  `600` weight, bottom border `--color-border-strong`.
- Body rows: `--row-height-default`, alternating background optional (
  `--color-bg` / `--color-bg-subtle` at 50%), bottom border `--color-border`.
- Numeric columns right-aligned, mono font.
- DevOnboard vs plain-agent comparison columns sit side-by-side with a vertical
  divider (`--color-border-strong`) between mode groups.

---

## 10. Banners / Warning States

- Full-width within panel, `--radius-sm`, padding `--space-2`/`--space-3`.
- Background = semantic `*-bg` token at full opacity, left border 3px solid in the
  semantic color, icon (16px) + text (`--text-sm`).
- Warning banner copy must name the specific issue (e.g. "GitHub metadata
  unavailable — showing commit-only history") — never a generic "Something went wrong".

---

## 11. Skeleton / Loading

- Skeleton blocks: `--color-bg-muted`, `--radius-sm`, shimmer animation
  (180ms ease, respects `prefers-reduced-motion` → static block, no shimmer).
- Streaming answer: text appears progressively; show a small animated cursor/dot
  at the end of the streaming line, removed on completion.
