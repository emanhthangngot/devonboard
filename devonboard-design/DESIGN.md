# DESIGN.md — DevOnboard UI/UX Contract

> This file is the entrypoint an AI coding agent (Claude Code, Cursor, Codex, etc.)
> reads before building or modifying any DevOnboard frontend surface.
> It binds the design system in `design-systems/devonboard-default/DESIGN.md`
> and the UX flow rules in `ux-flows/`.

---

## 1. How To Use This Bundle

1. Read `design-systems/devonboard-default/DESIGN.md` first — it defines tokens,
   typography, color, spacing, and component visual rules.
2. Read `ux-flows/layout.md` for screen structure and panel composition.
3. Read `ux-flows/states.md` for every required UI state (loading, empty, error, streaming).
4. Read `ux-flows/components.md` for component-level behavior specs (CitationCard,
   HistoryPanel, QueryPanel, etc.).
5. Read `ux-flows/accessibility.md` and `ux-flows/copy-tone.md` before writing any
   user-facing string or interactive control.

When generating or editing UI code, the agent must:

- Use only the tokens defined in `design-systems/devonboard-default/tokens.md`.
- Implement every state listed in `ux-flows/states.md` for the component being built —
  do not ship a component with only the "happy path" state.
- Never invent new color roles, spacing values, or typography sizes outside the token set.
- Treat citations, evidence, and warnings as first-class UI elements, not afterthoughts.

---

## 2. Source Of Truth Precedence

If there is a conflict between documents, resolve in this order:

1. `constitution.md` / `spec.md` (product principles — not included in this bundle,
   but the agent must not violate P1–P7 from the project constitution).
2. `ux-flows/*.md` (behavior and structure).
3. `design-systems/devonboard-default/DESIGN.md` (visual tokens and styling).

Product correctness (citations, evidence, defensive UX states) always wins over
visual polish. A beautiful screen that hides missing evidence is a defect.

---

## 3. Non-Negotiable UX Principles (from constitution.md / FRONTEND.md)

- **Evidence before synthesis** — every answer that cites historical rationale must
  show citations inline or in an adjacent panel. No citation = no rationale claim shown.
- **Copilot, not autopilot** — UI must always expose raw evidence, retrieved context,
  and a way to mark an answer unsupported.
- **Explicit empty/error/stale states** — never let a panel silently show nothing.
- **Dense, engineer-native** — this is a working tool for engineers, not a marketing site.
  Favor information density over whitespace-heavy "consumer app" layouts.
- **Light theme, projector-readable** — default theme must hold up on a projector
  in a bright room.

---

## 4. File Map

```text
devonboard-design/
├── DESIGN.md                          (this file)
├── design-systems/
│   └── devonboard-default/
│       ├── DESIGN.md                  (visual system overview)
│       ├── tokens.md                  (color/type/spacing tokens)
│       └── components.md              (visual component styling)
└── ux-flows/
    ├── layout.md                      (screen/panel structure)
    ├── states.md                      (required states matrix)
    ├── components.md                  (behavioral component specs)
    ├── accessibility.md               (a11y rules)
    └── copy-tone.md                   (microcopy & tone rules)
```
