# DESIGN.md — devonboard-default Design System

> Hand-authored design system for DevOnboard. "Dense, engineer-native, light theme,
> projector-readable" per FRONTEND.md §5.

---

## 1. Visual Identity

DevOnboard looks like a **developer tool**, not a marketing product. Reference points:
GitHub's code review UI, Linear's density, a graph-explorer/IDE sidebar. Avoid large
hero sections, soft gradients, oversized illustration, or consumer-app whitespace.

Core traits:

- Light background, dark text, high contrast for projector use.
- Information-dense panels with compact rows, not card grids with large padding.
- Monospace for code, file paths, IDs, commit hashes. Sans-serif for prose/UI labels.
- Color is reserved for **semantic meaning** (evidence type badges), not decoration.

---

## 2. Layout Skeleton

Three-pane workspace (see `ux-flows/layout.md` for full spec):

```text
┌─────────────────────────────────────────────────────────┐
│ TopNav (repo, scan/ingest status, benchmark link)        │
├───────────────┬─────────────────────────┬───────────────┤
│ Left           │ Center                   │ Right         │
│ Graph/File Nav │ Q&A thread / answers     │ History/Why   │
│ (~240px)       │ (flexible)               │ (~320px)      │
└───────────────┴─────────────────────────┴───────────────┘
```

Panels are resizable but have min-widths. Center pane never collapses below 480px;
side panels collapse to icon rails below that.

---

## 3. Component Visual Reference

See `tokens.md` for raw values and `components.md` for per-component styling.
Behavioral specs (what each component must do, not look like) live in
`ux-flows/components.md`.

---

## 4. Theming

- **Default and only MVP theme: Light.** Dark mode is explicitly out of scope for MVP
  (do not build a theme switcher unless asked).
- All colors must be defined as CSS variables in `tokens.md` so a future dark theme
  can be added without rewriting components.

---

## 5. Iconography

- Use a single icon set (e.g. Lucide) at 16px (inline/badges) and 20px (nav/buttons).
- Icons always pair with a text label in primary navigation — icon-only buttons are
  reserved for repeatable row actions (copy, open, retry, dismiss).

---

## 6. Motion

- Motion is functional, not decorative: streaming text reveal, panel expand/collapse,
  skeleton shimmer for loading states, subtle highlight flash when a citation is
  clicked and its source scrolls into view.
- Durations: 120–180ms for micro-interactions (hover, focus), 200–250ms for
  panel/accordion transitions. No motion longer than 300ms.
- Respect `prefers-reduced-motion`: disable shimmer/flash, keep instant state changes.
