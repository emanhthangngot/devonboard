# accessibility.md — Accessibility Rules

---

## 1. Color & Contrast

- All text/background pairs from `tokens.md` must meet WCAG AA (4.5:1 for body text,
  3:1 for large text ≥18px).
- Semantic evidence badges (structural/historical/claim/risk) must never be the
  *only* signal — always pair color with a text label or icon (do not rely on
  color alone to convey evidence type, per WCAG 1.4.1).
- Focus states use a visible 2px outline (`--color-primary` at 30% + border), never
  `outline: none` without a replacement.

---

## 2. Keyboard Navigation

- Full keyboard operability for: panel resize/collapse, tree navigation (arrow keys),
  query input submit (Enter/Shift+Enter), citation chip activation (Enter/Space),
  modal/panel dismissal (Escape).
- Tab order follows visual order: TopNav → Left panel → Center panel → Right panel.
- Citation chips and CitationCards are focusable buttons/links, not divs with
  onClick only.

---

## 3. Screen Reader Support

- Streaming answers: use `aria-live="polite"` on the answer container so screen
  readers announce incremental content without interrupting.
- Status pills (scan/ingest) use `aria-label` describing full state, e.g.
  "Scan status: in progress" not just an icon.
- Empty/warning/error states are real text content (not background images or
  icon-only), readable by screen readers.
- Evidence type badges include visually-hidden text (e.g. "Historical evidence:")
  in addition to the visible short label.

---

## 4. Motion & Animation

- Respect `prefers-reduced-motion: reduce`:
  - Disable shimmer/skeleton animations (render static placeholder).
  - Disable highlight-flash on citation click (use instant background change instead).
  - Streaming text still appears progressively (this is content delivery, not
    decorative motion) but without cursor-blink animation.

---

## 5. Forms & Inputs

- Every input has a visible or `aria-label` label — no placeholder-only labeling.
- Inline validation/error messages are associated via `aria-describedby`.
- Benchmark manual rating inputs (human quality score) have explicit numeric
  labels (1–5) with text equivalents, not star-icon-only ratings.

---

## 6. Responsive / Zoom

- UI must remain usable at 200% browser zoom without horizontal scroll on the
  center panel (side panels may scroll independently).
- Minimum touch target size 32x32px for icon-only buttons on touch-capable
  viewports.
