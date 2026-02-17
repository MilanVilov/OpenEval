# Skill: UI Design — Cursor Dark Midnight Theme

This skill defines the visual design system for all ai-eval frontend pages. Every template, CSS rule, and HTML component MUST follow these specifications.

---

## Design Philosophy

- **Ultra-dark, blue-shifted neutrals** — backgrounds in the `#0d`–`#14` range with a midnight blue-gray undertone. Never pure black.
- **Minimal contrast borders** — borders provide structure but stay nearly invisible (~10–15% luminance difference from surface).
- **Blue-to-indigo accent spectrum** — `#3b82f6` as the primary accent, shifting toward `#6366f1` / `#8b5cf6` for AI/generative features.
- **Clean, tight typography** — Inter/system sans-serif at 13px, minimal letter-spacing, medium weight for emphasis.
- **Consistent 4px grid** — all spacing and sizing in multiples of 4.
- **Soft radius, no hard edges** — 6–8px radius on interactive elements.
- **Subtle elevation via shadow, not color lift** — depth comes from shadow opacity, not brighter surfaces.
- **Restrained color usage** — semantic colors (red/green/amber) only for status; everything else is monochromatic + blue accent.

---

## Color Palette

### Backgrounds

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | `#0d1117` | Page body, deepest background |
| `--bg-secondary` | `#14141b` | Sidebar, panel surfaces |
| `--bg-card` | `#1a1a24` | Cards, dropdowns, elevated containers |
| `--bg-input` | `#1c1c28` | Form fields, search bars |
| `--bg-hover` | `#1e1e2e` | Hover state for rows, list items |

### Borders

| Token | Hex | Usage |
|-------|-----|-------|
| `--border-primary` | `#2a2a3c` | Panel dividers, card borders |
| `--border-muted` | `#1e1e2e` | Subtle separators, table row dividers |
| `--border-focus` | `#3b82f6` | Input focus ring |
| `--border-hover` | `#2e2e42` | Interactive element hover border |

### Text

| Token | Hex | Usage |
|-------|-----|-------|
| `--text-primary` | `#e4e4e8` | Body text, headings |
| `--text-secondary` | `#8b8b9e` | Descriptions, labels, metadata |
| `--text-disabled` | `#4a4a5c` | Inactive elements |
| `--text-link` | `#60a5fa` | Hyperlinks |

### Accent

| Token | Hex | Usage |
|-------|-----|-------|
| `--accent-primary` | `#3b82f6` | Primary buttons, active indicators, focus rings |
| `--accent-secondary` | `#6366f1` | Hover on accent elements, AI feature highlights |
| `--accent-purple` | `#8b5cf6` | Gradient endpoint, special features |
| `--accent-muted` | `rgba(59,130,246,0.12)` | Selected item backgrounds, badges |

### Semantic / Status

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-success` | `#22c55e` | Passed evals, success states |
| `--color-error` | `#ef4444` | Failed evals, errors, destructive actions |
| `--color-warning` | `#f59e0b` | Warnings, caution states |
| `--color-info` | `#3b82f6` | Informational badges |

---

## Typography

| Property | Value |
|----------|-------|
| **UI font stack** | `"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif` |
| **Mono font stack** | `"SF Mono", "Fira Code", "JetBrains Mono", Menlo, Monaco, monospace` |
| **Base font size** | `13px` |
| **Line height** | `1.5` |
| **Font weight (normal)** | `400` |
| **Font weight (semibold)** | `500` (headings, labels, active tabs) |
| **Font weight (bold)** | `600` (page titles, emphasis) |
| **Letter spacing** | `0` to `0.01em` |

### Heading Scale

| Level | Size | Weight |
|-------|------|--------|
| Page title (`h1`) | `20px` | `600` |
| Section title (`h2`) | `16px` | `600` |
| Subsection (`h3`) | `14px` | `500` |
| Body | `13px` | `400` |
| Small/caption | `11px` | `400`–`500` |

---

## Spacing

Base unit: **4px**. All spacing must be a multiple of 4.

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | `4px` | Tight gaps, icon-to-text |
| `--space-2` | `8px` | Between related elements |
| `--space-3` | `12px` | Section gaps |
| `--space-4` | `16px` | Card inner padding, standard gap |
| `--space-5` | `20px` | Card inner padding (large), page padding |
| `--space-6` | `24px` | Page-level margins |

---

## Border Radius

| Element | Radius |
|---------|--------|
| Buttons | `6px` |
| Input fields | `6px` |
| Cards, panels | `8px` |
| Dropdowns, modals | `12px` |
| Tooltips, badges | `4px` |
| Pills, tags | `9999px` |

---

## Components

### Buttons

**Primary:**
```css
.btn-primary {
  background: var(--accent-primary);    /* #3b82f6 */
  color: #ffffff;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 150ms ease;
}
.btn-primary:hover {
  background: #2563eb;
}
```

**Secondary / Ghost:**
```css
.btn-secondary {
  background: transparent;
  color: var(--text-primary);           /* #e4e4e8 */
  border: 1px solid var(--border-primary); /* #2a2a3c */
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 400;
  cursor: pointer;
  transition: all 150ms ease;
}
.btn-secondary:hover {
  background: var(--bg-hover);          /* #1e1e2e */
  border-color: var(--border-hover);    /* #2e2e42 */
}
```

**Danger:**
```css
.btn-danger {
  background: transparent;
  color: var(--color-error);            /* #ef4444 */
  border: 1px solid var(--color-error);
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  transition: all 150ms ease;
}
.btn-danger:hover {
  background: rgba(239, 68, 68, 0.1);
}
```

### Input Fields

```css
.input {
  background: var(--bg-input);          /* #1c1c28 */
  color: var(--text-primary);           /* #e4e4e8 */
  border: 1px solid var(--border-primary); /* #2a2a3c */
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 13px;
  font-family: inherit;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}
.input:focus {
  border-color: var(--border-focus);    /* #3b82f6 */
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
  outline: none;
}
.input::placeholder {
  color: var(--text-disabled);          /* #4a4a5c */
}
```

### Textarea (Prompt Editor)

Same as input, but with:
```css
.textarea {
  min-height: 120px;
  resize: vertical;
  font-family: var(--font-mono);        /* monospace for prompts */
  line-height: 1.6;
}
```

### Cards

```css
.card {
  background: var(--bg-card);           /* #1a1a24 */
  border: 1px solid var(--border-muted); /* #1e1e2e */
  border-radius: 8px;
  padding: 20px;
}
```

### Tables

```css
.table {
  width: 100%;
  border-collapse: collapse;
}
.table th {
  background: var(--bg-secondary);      /* #14141b */
  color: var(--text-secondary);         /* #8b8b9e */
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 10px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border-primary);
}
.table td {
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-muted); /* #1e1e2e */
  font-size: 13px;
  color: var(--text-primary);
}
.table tr:hover td {
  background: rgba(255, 255, 255, 0.03);
}
```

### Select / Dropdown

Same styling as `.input`. Use Alpine.js for custom dropdowns where needed.

### Badges / Pills

```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 500;
}
.badge-success {
  background: rgba(34, 197, 94, 0.12);
  color: #22c55e;
}
.badge-error {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
}
.badge-info {
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
}
.badge-warning {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
}
```

### Progress Bar

```css
.progress-bar {
  width: 100%;
  height: 6px;
  background: var(--bg-input);
  border-radius: 9999px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-purple));
  border-radius: 9999px;
  transition: width 300ms ease;
}
```

### Summary Stats (Run Detail)

Use a horizontal row of stat cards:
```css
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-muted);
  border-radius: 8px;
  padding: 16px 20px;
  text-align: center;
}
.stat-card .stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}
.stat-card .stat-label {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 4px;
}
```

### Navigation / Sidebar

```css
.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 400;
  transition: all 150ms ease;
  text-decoration: none;
}
.nav-item:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.04);
}
.nav-item.active {
  color: var(--text-primary);
  background: var(--accent-muted);      /* rgba(59,130,246,0.12) */
  border-left: 2px solid var(--accent-primary);
}
```

---

## Shadows

| Level | Value | Usage |
|-------|-------|-------|
| Subtle | `0 1px 2px rgba(0,0,0,0.3)` | Cards resting state |
| Medium | `0 4px 12px rgba(0,0,0,0.4)` | Dropdowns, popovers |
| Heavy | `0 8px 30px rgba(0,0,0,0.5)` | Modals |
| Backdrop | `rgba(0,0,0,0.6)` | Modal overlay |

---

## Scrollbars

```css
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.14);
}
```

---

## Layout Patterns

### Page Layout

- Sidebar: 220px wide, fixed, `var(--bg-secondary)` background.
- Main content: flex-grow, padded `24px`, max-width `1200px` for readability.
- Top bar: optional, same `var(--bg-secondary)`, 48px height, page title + breadcrumb.

### Form Layout

- Labels above inputs, `var(--text-secondary)`, `11px`, `font-weight: 500`, uppercase.
- Vertical gap between form groups: `16px`.
- Action buttons at bottom, right-aligned, primary + secondary pair.

### Grid

- Use CSS Grid or Flexbox with `gap: 16px`.
- Stat cards in run detail: 4-column grid on desktop, 2-column on mobile.
- Results table: full-width, no horizontal scroll (truncate long text with `…`).

---

## Transitions

All interactive state changes use `150ms ease`:

```css
* {
  transition-duration: 150ms;
  transition-timing-function: ease;
}
```

Apply to: `background`, `border-color`, `color`, `box-shadow`, `opacity`, `transform`.

---

## Icons

- Use **Lucide Icons** (the open-source fork of Feather Icons).
- Size: 16px for inline, 20px for nav/action buttons.
- Color: inherits from text color (`currentColor`).
- Stroke width: 1.5–2px.

---

## Do's and Don'ts

### Do

- Use CSS custom properties (the tokens above) for all colors.
- Keep surfaces dark — never use backgrounds lighter than `#1e1e2e`.
- Use the accent blue sparingly — only for interactive elements and active states.
- Match the 4px spacing grid exactly.
- Use `font-weight: 500` or `600` for emphasis, never `700`+ (too heavy for this theme).

### Don't

- Never use pure white (`#ffffff`) for backgrounds or large text areas.
- Never use pure black (`#000000`) for backgrounds — always add the blue tint.
- Don't use bright/saturated colors for non-status purposes.
- Don't round corners above `12px` (except pills at `9999px`).
- Don't use box shadows lighter than `rgba(0,0,0,0.3)` — they'll look washed out.
- Don't mix font families — body is Inter, code is monospace. No exceptions.
