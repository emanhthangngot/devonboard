# tokens.md — Design Tokens (devonboard-default)

> All values below must be implemented as CSS variables (e.g. Tailwind theme extension
> or `:root` custom properties). Agents must not introduce ad-hoc hex codes, px values,
> or font sizes outside this file.

---

## 1. Color Tokens

### 1.1 Base / Neutral

| Token | Value | Usage |
|---|---|---|
| `--color-bg` | `#FFFFFF` | App background |
| `--color-bg-subtle` | `#F6F7F9` | Panel background, code blocks |
| `--color-bg-muted` | `#EEF0F3` | Hover rows, input backgrounds |
| `--color-border` | `#D9DCE3` | Default borders, dividers |
| `--color-border-strong` | `#B8BDC9` | Focused/active borders |
| `--color-text` | `#0F1419` | Primary text |
| `--color-text-muted` | `#5B6472` | Secondary text, metadata |
| `--color-text-faint` | `#8A93A3` | Placeholder, disabled |

### 1.2 Brand / Action

| Token | Value | Usage |
|---|---|---|
| `--color-primary` | `#2453E0` | Primary buttons, links, active nav |
| `--color-primary-hover` | `#1B3FB8` | Primary hover |
| `--color-primary-subtle` | `#E8EDFC` | Selected row background |

### 1.3 Semantic Evidence Badges (FRONTEND.md §5)

| Token | Value | Usage |
|---|---|---|
| `--color-structural` | `#2453E0` (blue) | Structural evidence badges |
| `--color-structural-bg` | `#E8EDFC` | Structural badge background |
| `--color-historical` | `#1F8A4C` (green) | Historical source badges |
| `--color-historical-bg` | `#E6F6EC` | Historical badge background |
| `--color-claim` | `#B5790A` (amber) | Claim/rationale badges |
| `--color-claim-bg` | `#FBF1DE` | Claim badge background |
| `--color-risk` | `#C3362C` (red) | Risk/contradiction badges, warnings |
| `--color-risk-bg` | `#FBE9E7` | Risk badge background |

### 1.4 Status

| Token | Value | Usage |
|---|---|---|
| `--color-success` | `#1F8A4C` | Scan/ingest success states |
| `--color-warning` | `#B5790A` | Stale graph, low confidence |
| `--color-error` | `#C3362C` | API/token errors |
| `--color-info` | `#2453E0` | Informational banners |

---

## 2. Typography Tokens

| Token | Font | Usage |
|---|---|---|
| `--font-sans` | Inter, system-ui, sans-serif | UI labels, prose, navigation |
| `--font-mono` | "JetBrains Mono", "SF Mono", monospace | File paths, code, commit hashes, IDs, JSON |

### Type Scale

| Token | Size / Line-height | Usage |
|---|---|---|
| `--text-xs` | 11px / 16px | Badges, timestamps, metadata |
| `--text-sm` | 13px / 18px | Body text, table cells, default UI |
| `--text-base` | 14px / 20px | Primary reading text (answers) |
| `--text-md` | 16px / 24px | Panel headers |
| `--text-lg` | 18px / 26px | Page-level titles (rare) |

Weights: `400` (body), `500` (labels, emphasis), `600` (headers only). Never use `700+`.

---

## 3. Spacing Tokens

8px base grid.

| Token | Value |
|---|---|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 24px |
| `--space-6` | 32px |

Default component padding: `--space-2` to `--space-3`. Avoid `--space-5`+ inside
data-dense panels (graph nav, history list, citation cards).

---

## 4. Radius & Elevation

| Token | Value | Usage |
|---|---|---|
| `--radius-sm` | 4px | Badges, inputs, buttons |
| `--radius-md` | 6px | Cards, panels |
| `--shadow-sm` | `0 1px 2px rgba(15,20,25,0.06)` | Cards on hover, dropdowns |
| `--shadow-md` | `0 4px 12px rgba(15,20,25,0.10)` | Modals, popovers |

No shadows on static panels — borders (`--color-border`) define separation, not elevation.

---

## 5. Layout Tokens

| Token | Value | Usage |
|---|---|---|
| `--topnav-height` | 48px | TopNav |
| `--panel-left-width` | 240px | Graph/file nav default width |
| `--panel-right-width` | 320px | History/Why inspector default width |
| `--panel-min-center` | 480px | Minimum center pane width |
| `--rail-collapsed-width` | 48px | Collapsed side panel icon rail |

---

## 6. Component Sizing

| Token | Value | Usage |
|---|---|---|
| `--row-height-compact` | 28px | List rows (file tree, history list) |
| `--row-height-default` | 36px | Table rows, inputs |
| `--button-height` | 32px | Default button |
| `--badge-height` | 18px | Evidence type badges |
