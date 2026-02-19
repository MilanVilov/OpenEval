# Skill: UI Design — Dark Midnight Theme with Tailwind + Shadcn/ui

This skill defines the visual design system for all ai-eval frontend pages. Every React component, Tailwind class, and Shadcn/ui usage MUST follow these specifications.

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
- **Tailwind-first** — use utility classes for all styling. Custom CSS is a last resort.
- **Shadcn/ui components** — use the component library for all standard UI elements. Don't reinvent buttons, inputs, cards, etc.

---

## Color Palette

All theme colors are defined in `tailwind.config.ts` and mapped to CSS variables in `globals.css` for Shadcn/ui integration.

### Tailwind Config

```ts
// tailwind.config.ts
import type { Config } from 'tailwindcss';

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#0d1117',
          secondary: '#14141b',
          card: '#1a1a24',
          input: '#1c1c28',
          hover: '#1e1e2e',
        },
        border: {
          DEFAULT: '#2a2a3c',
          muted: '#1e1e2e',
          focus: '#3b82f6',
          hover: '#2e2e42',
        },
        foreground: {
          DEFAULT: '#e4e4e8',
          secondary: '#8b8b9e',
          disabled: '#4a4a5c',
          link: '#60a5fa',
        },
        accent: {
          DEFAULT: '#3b82f6',
          secondary: '#6366f1',
          purple: '#8b5cf6',
          muted: 'rgba(59,130,246,0.12)',
        },
        success: '#22c55e',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6',
      },
      fontFamily: {
        sans: ['"Inter"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'system-ui', 'sans-serif'],
        mono: ['"SF Mono"', '"Fira Code"', '"JetBrains Mono"', 'Menlo', 'Monaco', 'monospace'],
      },
      fontSize: {
        xs: ['11px', { lineHeight: '1.5' }],
        sm: ['13px', { lineHeight: '1.5' }],
        base: ['14px', { lineHeight: '1.5' }],
        lg: ['16px', { lineHeight: '1.5' }],
        xl: ['20px', { lineHeight: '1.4' }],
      },
      borderRadius: {
        sm: '4px',
        DEFAULT: '6px',
        md: '8px',
        lg: '12px',
        full: '9999px',
      },
      boxShadow: {
        subtle: '0 1px 2px rgba(0,0,0,0.3)',
        medium: '0 4px 12px rgba(0,0,0,0.4)',
        heavy: '0 8px 30px rgba(0,0,0,0.5)',
      },
      spacing: {
        '1': '4px',
        '2': '8px',
        '3': '12px',
        '4': '16px',
        '5': '20px',
        '6': '24px',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
} satisfies Config;
```

### CSS Variables for Shadcn/ui (`globals.css`)

Shadcn/ui reads its colors from CSS variables. Map the theme tokens here:

```css
/* frontend/src/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Backgrounds */
    --background: 222 22% 7%;          /* #0d1117 */
    --secondary: 240 16% 9%;           /* #14141b */
    --card: 240 16% 12%;               /* #1a1a24 */
    --input: 240 16% 13%;              /* #1c1c28 */
    --muted: 240 16% 15%;              /* #1e1e2e */

    /* Foreground */
    --foreground: 240 5% 91%;          /* #e4e4e8 */
    --muted-foreground: 240 10% 58%;   /* #8b8b9e */

    /* Borders */
    --border: 240 18% 20%;             /* #2a2a3c */
    --ring: 217 91% 60%;               /* #3b82f6 */

    /* Accent / Primary */
    --primary: 217 91% 60%;            /* #3b82f6 */
    --primary-foreground: 0 0% 100%;   /* #ffffff */

    /* Destructive */
    --destructive: 0 84% 60%;          /* #ef4444 */
    --destructive-foreground: 0 0% 100%;

    /* Popover */
    --popover: 240 16% 12%;            /* #1a1a24 */
    --popover-foreground: 240 5% 91%;  /* #e4e4e8 */

    /* Radius */
    --radius: 6px;
  }

  body {
    @apply bg-background text-foreground font-sans text-sm antialiased;
  }
}

/* Scrollbar styling */
@layer base {
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
}
```

### Quick Reference Table

| Token | Hex | Tailwind class |
|-------|-----|----------------|
| Background | `#0d1117` | `bg-background` |
| Secondary bg | `#14141b` | `bg-background-secondary` |
| Card bg | `#1a1a24` | `bg-background-card` |
| Input bg | `#1c1c28` | `bg-background-input` |
| Hover bg | `#1e1e2e` | `bg-background-hover` |
| Border | `#2a2a3c` | `border-border` |
| Border muted | `#1e1e2e` | `border-border-muted` |
| Border focus | `#3b82f6` | `border-border-focus` / `ring-border-focus` |
| Text primary | `#e4e4e8` | `text-foreground` |
| Text secondary | `#8b8b9e` | `text-foreground-secondary` |
| Text disabled | `#4a4a5c` | `text-foreground-disabled` |
| Link | `#60a5fa` | `text-foreground-link` |
| Accent | `#3b82f6` | `bg-accent` / `text-accent` |
| Accent secondary | `#6366f1` | `bg-accent-secondary` |
| Accent purple | `#8b5cf6` | `bg-accent-purple` |
| Accent muted | `rgba(59,130,246,0.12)` | `bg-accent-muted` |
| Success | `#22c55e` | `text-success` / `bg-success` |
| Error | `#ef4444` | `text-error` / `bg-error` |
| Warning | `#f59e0b` | `text-warning` / `bg-warning` |
| Info | `#3b82f6` | `text-info` / `bg-info` |

---

## Typography

### Font Stacks

| Purpose | Tailwind class | Fonts |
|---------|---------------|-------|
| UI text | `font-sans` | Inter, -apple-system, BlinkMacSystemFont, Segoe UI, system-ui, sans-serif |
| Code/prompts | `font-mono` | SF Mono, Fira Code, JetBrains Mono, Menlo, Monaco, monospace |

### Heading Scale

| Level | Tailwind classes | Size | Weight |
|-------|-----------------|------|--------|
| Page title (`h1`) | `text-xl font-semibold` | 20px | 600 |
| Section title (`h2`) | `text-lg font-semibold` | 16px | 600 |
| Subsection (`h3`) | `text-base font-medium` | 14px | 500 |
| Body | `text-sm font-normal` | 13px | 400 |
| Small/caption | `text-xs font-normal` or `text-xs font-medium` | 11px | 400–500 |

### Usage

```tsx
<h1 className="text-xl font-semibold text-foreground">Eval Runs</h1>
<p className="text-sm text-foreground-secondary">Select a configuration to run.</p>
<span className="text-xs font-medium uppercase tracking-wide text-foreground-secondary">Status</span>
```

---

## Spacing

Base unit: **4px**. All spacing must be a multiple of 4. The Tailwind config maps spacing values directly:

| Tailwind class | Value | Usage |
|----------------|-------|-------|
| `p-1` / `gap-1` | 4px | Tight gaps, icon-to-text |
| `p-2` / `gap-2` | 8px | Between related elements |
| `p-3` / `gap-3` | 12px | Section gaps |
| `p-4` / `gap-4` | 16px | Card inner padding, standard gap |
| `p-5` / `gap-5` | 20px | Card inner padding (large), page padding |
| `p-6` / `gap-6` | 24px | Page-level margins |

---

## Border Radius

| Element | Tailwind class | Value |
|---------|---------------|-------|
| Badges, tooltips | `rounded-sm` | 4px |
| Buttons, inputs | `rounded` | 6px |
| Cards, panels | `rounded-md` | 8px |
| Dropdowns, modals | `rounded-lg` | 12px |
| Pills, tags | `rounded-full` | 9999px |

---

## Components

All standard UI elements use Shadcn/ui components. Customize with Tailwind classes.

### Button

```tsx
import { Button } from '@/components/ui/button';

// Primary action
<Button>Create Config</Button>

// Secondary / outline
<Button variant="outline">Cancel</Button>

// Ghost (minimal)
<Button variant="ghost">Settings</Button>

// Danger / destructive
<Button variant="destructive">Delete Run</Button>

// With icon
import { Play } from 'lucide-react';
<Button>
  <Play className="mr-2 h-4 w-4" />
  Start Run
</Button>

// Small variant
<Button size="sm">View</Button>
```

### Input

```tsx
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

<div className="space-y-2">
  <Label className="text-xs font-medium uppercase tracking-wide text-foreground-secondary">
    Config Name
  </Label>
  <Input
    placeholder="My eval config"
    className="bg-background-input border-border"
  />
</div>
```

### Textarea (Prompt Editor)

```tsx
import { Textarea } from '@/components/ui/textarea';

<Textarea
  placeholder="Enter your prompt template..."
  className="bg-background-input border-border font-mono min-h-[120px]"
/>
```

### Card

```tsx
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';

<Card className="bg-background-card border-border-muted">
  <CardHeader>
    <CardTitle className="text-lg font-semibold">Eval Config</CardTitle>
  </CardHeader>
  <CardContent>
    <p className="text-sm text-foreground-secondary">
      Configure your evaluation parameters.
    </p>
  </CardContent>
  <CardFooter className="flex justify-end gap-2">
    <Button variant="outline">Cancel</Button>
    <Button>Save</Button>
  </CardFooter>
</Card>
```

### Table

```tsx
import {
  Table, TableHeader, TableBody, TableRow,
  TableHead, TableCell,
} from '@/components/ui/table';

<Table>
  <TableHeader>
    <TableRow className="bg-background-secondary border-border">
      <TableHead className="text-xs font-semibold uppercase tracking-wide text-foreground-secondary">
        Name
      </TableHead>
      <TableHead className="text-xs font-semibold uppercase tracking-wide text-foreground-secondary">
        Status
      </TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow className="border-border-muted hover:bg-[rgba(255,255,255,0.03)]">
      <TableCell className="text-sm">My Config</TableCell>
      <TableCell><StatusBadge status="passed" /></TableCell>
    </TableRow>
  </TableBody>
</Table>
```

### Badge

```tsx
import { Badge } from '@/components/ui/badge';

// Status badges — use inline Tailwind for semantic colors
<Badge className="bg-success/10 text-success border-0">Passed</Badge>
<Badge className="bg-error/10 text-error border-0">Failed</Badge>
<Badge className="bg-warning/10 text-warning border-0">Running</Badge>
<Badge className="bg-info/10 text-foreground-link border-0">Pending</Badge>

// Reusable pattern:
interface StatusBadgeProps {
  status: 'passed' | 'failed' | 'running' | 'pending';
}

const statusStyles: Record<string, string> = {
  passed: 'bg-success/10 text-success',
  failed: 'bg-error/10 text-error',
  running: 'bg-warning/10 text-warning',
  pending: 'bg-info/10 text-foreground-link',
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <Badge className={`${statusStyles[status]} border-0 rounded-full`}>
      {status}
    </Badge>
  );
}
```

### Progress

```tsx
import { Progress } from '@/components/ui/progress';

<Progress
  value={75}
  className="h-1.5 bg-background-input [&>div]:bg-gradient-to-r [&>div]:from-accent [&>div]:to-accent-purple"
/>
```

### Select / Dropdown

```tsx
import {
  Select, SelectTrigger, SelectValue,
  SelectContent, SelectItem,
} from '@/components/ui/select';

<Select>
  <SelectTrigger className="bg-background-input border-border">
    <SelectValue placeholder="Choose a model" />
  </SelectTrigger>
  <SelectContent className="bg-background-card border-border">
    <SelectItem value="gpt-4o">GPT-4o</SelectItem>
    <SelectItem value="gpt-4o-mini">GPT-4o Mini</SelectItem>
  </SelectContent>
</Select>
```

### Dialog / Modal

```tsx
import {
  Dialog, DialogTrigger, DialogContent,
  DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';

<Dialog>
  <DialogTrigger asChild>
    <Button variant="destructive">Delete</Button>
  </DialogTrigger>
  <DialogContent className="bg-background-card border-border">
    <DialogHeader>
      <DialogTitle>Confirm Deletion</DialogTitle>
    </DialogHeader>
    <p className="text-sm text-foreground-secondary">
      This action cannot be undone.
    </p>
    <DialogFooter>
      <Button variant="outline">Cancel</Button>
      <Button variant="destructive">Delete</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Summary Stats (Run Detail)

```tsx
interface StatCardProps {
  label: string;
  value: string | number;
}

export function StatCard({ label, value }: StatCardProps) {
  return (
    <Card className="bg-background-card border-border-muted text-center p-4">
      <div className="text-2xl font-semibold text-foreground">{value}</div>
      <div className="text-xs font-medium uppercase tracking-wide text-foreground-secondary mt-1">
        {label}
      </div>
    </Card>
  );
}

// Usage: 4-column grid
<div className="grid grid-cols-4 gap-4">
  <StatCard label="Total" value={100} />
  <StatCard label="Passed" value={87} />
  <StatCard label="Failed" value={13} />
  <StatCard label="Avg Score" value="0.87" />
</div>
```

### Navigation / Sidebar

```tsx
import { NavLink } from 'react-router-dom';
import { BarChart3, Settings, Play, Database, FileText } from 'lucide-react';

interface NavItemProps {
  to: string;
  icon: React.ReactNode;
  label: string;
}

function NavItem({ to, icon, label }: NavItemProps) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-2 rounded px-3 py-2 text-sm transition-all duration-150
         ${isActive
           ? 'bg-accent-muted text-foreground border-l-2 border-accent'
           : 'text-foreground-secondary hover:text-foreground hover:bg-[rgba(255,255,255,0.04)]'
         }`
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}

export function Sidebar() {
  return (
    <aside className="flex w-[220px] flex-col bg-background-secondary border-r border-border p-4 gap-1">
      <NavItem to="/" icon={<BarChart3 className="h-4 w-4" />} label="Dashboard" />
      <NavItem to="/configs" icon={<Settings className="h-4 w-4" />} label="Configs" />
      <NavItem to="/datasets" icon={<Database className="h-4 w-4" />} label="Datasets" />
      <NavItem to="/runs" icon={<Play className="h-4 w-4" />} label="Runs" />
      <NavItem to="/vector-stores" icon={<FileText className="h-4 w-4" />} label="Vector Stores" />
    </aside>
  );
}
```

---

## Layout Patterns

### App Shell

```tsx
// AppLayout.tsx
import { Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/Sidebar';

export function AppLayout() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1200px]">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
```

### Page Header

```tsx
interface PageHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">{title}</h1>
        {description && (
          <p className="text-sm text-foreground-secondary mt-1">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}
```

### Form Layout

```tsx
<form className="space-y-4 max-w-[600px]">
  <div className="space-y-2">
    <Label className="text-xs font-medium uppercase tracking-wide text-foreground-secondary">
      Name
    </Label>
    <Input className="bg-background-input border-border" />
  </div>

  <div className="space-y-2">
    <Label className="text-xs font-medium uppercase tracking-wide text-foreground-secondary">
      Prompt Template
    </Label>
    <Textarea className="bg-background-input border-border font-mono min-h-[120px]" />
  </div>

  <div className="flex justify-end gap-2 pt-4">
    <Button variant="outline">Cancel</Button>
    <Button type="submit">Save</Button>
  </div>
</form>
```

### Responsive Grid

```tsx
// Stat cards: 4-col desktop, 2-col mobile
<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
  {stats.map(s => <StatCard key={s.label} {...s} />)}
</div>

// Content cards: 3-col desktop, 1-col mobile
<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
  {items.map(item => <ItemCard key={item.id} {...item} />)}
</div>
```

---

## Shadows

Use the custom shadow utilities defined in `tailwind.config.ts`:

| Tailwind class | Value | Usage |
|----------------|-------|-------|
| `shadow-subtle` | `0 1px 2px rgba(0,0,0,0.3)` | Cards resting state |
| `shadow-medium` | `0 4px 12px rgba(0,0,0,0.4)` | Dropdowns, popovers |
| `shadow-heavy` | `0 8px 30px rgba(0,0,0,0.5)` | Modals |

Modal backdrop: Shadcn/ui `DialogOverlay` uses `bg-black/60` by default — keep this.

---

## Modern Animations

Animations are essential for creating a polished, engaging experience. Use them thoughtfully to guide attention and provide feedback. All animations use CSS transitions, `tailwindcss-animate`, and lightweight React hooks — no extra libraries required.

### Animation Principles

- **Purposeful**: Every animation should have a reason (feedback, guidance, delight)
- **Quick**: Keep durations short (150–800ms) to feel snappy
- **Natural**: Use appropriate easing (elastic for bounce, ease-out for smooth)
- **Layered**: Combine transforms (scale + fade, slide + fade) for rich motion

### Easing Reference

| Name | CSS value | Use for |
|------|-----------|---------|
| Smooth deceleration | `cubic-bezier(0.16, 1, 0.3, 1)` | Fades, slides, most UI |
| Elastic bounce | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Success icons, celebrations |
| Symmetric smooth | `cubic-bezier(0.4, 0, 0.2, 1)` | Transitions, morphing |
| Snappy | `cubic-bezier(0, 0, 0.2, 1)` | Quick state changes |

Define these in `globals.css` for reuse:

```css
@layer base {
  :root {
    --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
    --ease-elastic: cubic-bezier(0.34, 1.56, 0.64, 1);
    --ease-smooth: cubic-bezier(0.4, 0, 0.2, 1);
    --ease-snappy: cubic-bezier(0, 0, 0.2, 1);
  }
}
```

### Animation Durations Guide

| Animation Type | Duration | Tailwind class |
|---------------|----------|----------------|
| Button press / release | 100–150ms | `duration-150` |
| Color / state change | 200ms | `duration-200` |
| Card selection | 200ms | `duration-200` |
| Slide / fade entrance | 300ms | `duration-300` |
| Page transition | 300–400ms | `duration-300` |
| Success entrance | 600–800ms | `duration-700` |
| Complex celebration | 1500ms | custom |
| Stagger delay per item | 50–75ms | custom |

### CSS Keyframes

Add to `globals.css`:

```css
@layer utilities {
  @keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes fade-in-up {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes fade-in-down {
    from { opacity: 0; transform: translateY(-12px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes scale-in {
    from { opacity: 0; transform: scale(0.9); }
    to { opacity: 1; transform: scale(1); }
  }

  @keyframes scale-in-bounce {
    0% { opacity: 0; transform: scale(0); }
    60% { opacity: 1; transform: scale(1.08); }
    80% { transform: scale(0.96); }
    100% { transform: scale(1); }
  }

  @keyframes slide-in-right {
    from { opacity: 0; transform: translateX(16px); }
    to { opacity: 1; transform: translateX(0); }
  }

  @keyframes slide-in-left {
    from { opacity: 0; transform: translateX(-16px); }
    to { opacity: 1; transform: translateX(0); }
  }

  @keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }

  @keyframes pulse-ring {
    0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
    70% { box-shadow: 0 0 0 8px rgba(59, 130, 246, 0); }
    100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
  }

  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    10%, 50%, 90% { transform: translateX(-3px); }
    30%, 70% { transform: translateX(3px); }
  }

  .animate-fade-in { animation: fade-in 300ms var(--ease-out-expo) both; }
  .animate-fade-in-up { animation: fade-in-up 400ms var(--ease-out-expo) both; }
  .animate-fade-in-down { animation: fade-in-down 400ms var(--ease-out-expo) both; }
  .animate-scale-in { animation: scale-in 300ms var(--ease-out-expo) both; }
  .animate-scale-in-bounce { animation: scale-in-bounce 700ms var(--ease-elastic) both; }
  .animate-slide-in-right { animation: slide-in-right 300ms var(--ease-out-expo) both; }
  .animate-slide-in-left { animation: slide-in-left 300ms var(--ease-out-expo) both; }
  .animate-shimmer { animation: shimmer 2s linear infinite; }
  .animate-pulse-ring { animation: pulse-ring 1.5s ease-out infinite; }
  .animate-shake { animation: shake 400ms ease-in-out; }
}
```

### Transitions (Interactive State Changes)

All interactive state changes use smooth transitions:

```tsx
// Applied via Tailwind on interactive elements
<button className="transition-all duration-150 ease-in-out ...">

// Specific property transitions for performance
<div className="transition-colors duration-200 ...">
<div className="transition-transform duration-150 ...">
<div className="transition-[opacity,transform] duration-300 ...">
```

Properties to transition: `background`, `border-color`, `color`, `box-shadow`, `opacity`, `transform`.

### Button Press Animation

Scale down on press for tactile feedback:

```tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';

interface AnimatedButtonProps extends React.ComponentProps<typeof Button> {
  children: React.ReactNode;
}

export function AnimatedButton({ children, className, ...props }: AnimatedButtonProps) {
  const [pressed, setPressed] = useState(false);

  return (
    <Button
      className={cn(
        'transition-transform duration-150 ease-in-out',
        pressed && 'scale-[0.97]',
        className,
      )}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      {...props}
    >
      {children}
    </Button>
  );
}
```

### Card Selection Animation

Animate border and background on selection:

```tsx
interface SelectableCardProps {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

export function SelectableCard({ selected, onClick, children }: SelectableCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'cursor-pointer rounded-md p-4 transition-all duration-200 ease-[var(--ease-smooth)]',
        selected
          ? 'bg-accent-muted border-2 border-accent shadow-subtle'
          : 'bg-background-card border border-border-muted hover:border-border-hover hover:bg-background-hover',
      )}
    >
      {children}
    </div>
  );
}
```

### Page / Section Entrance Animation

Animate elements when they appear. Use `useAnimateOnMount` for simple fade-in-up:

```tsx
import { useEffect, useRef, useState } from 'react';

/** Triggers a CSS animation class after mount (with optional delay). */
export function useAnimateOnMount(delay = 0) {
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  return { ref, visible };
}

// Usage
function SectionHeader({ title }: { title: string }) {
  const { visible } = useAnimateOnMount();

  return (
    <h2
      className={cn(
        'text-lg font-semibold transition-all duration-500 ease-[var(--ease-out-expo)]',
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3',
      )}
    >
      {title}
    </h2>
  );
}
```

### Staggered List Animation

Stagger the entrance of list items for a polished feel:

```tsx
interface StaggeredListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  staggerMs?: number;
  className?: string;
}

export function StaggeredList<T>({
  items,
  renderItem,
  staggerMs = 60,
  className,
}: StaggeredListProps<T>) {
  return (
    <div className={className}>
      {items.map((item, index) => (
        <div
          key={index}
          className="animate-fade-in-up"
          style={{ animationDelay: `${index * staggerMs}ms` }}
        >
          {renderItem(item, index)}
        </div>
      ))}
    </div>
  );
}

// Usage
<StaggeredList
  items={configs}
  className="space-y-2"
  renderItem={(config) => <ConfigCard config={config} />}
/>
```

### Success Screen Animation

Bouncy scale entrance + staggered fade for celebration moments:

```tsx
import { useEffect, useState } from 'react';
import { CheckCircle } from 'lucide-react';

export function SuccessScreen({ title, subtitle }: { title: string; subtitle: string }) {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    const t1 = setTimeout(() => setStage(1), 200);   // icon bounces in
    const t2 = setTimeout(() => setStage(2), 500);   // text fades in
    const t3 = setTimeout(() => setStage(3), 700);   // action button appears
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, []);

  return (
    <div className="flex flex-col items-center justify-center gap-6 py-16 text-center">
      {/* Success icon — bouncy scale */}
      <div
        className={cn(
          'flex h-20 w-20 items-center justify-center rounded-full bg-success/10 transition-all duration-700',
          stage >= 1
            ? 'scale-100 opacity-100 ease-[var(--ease-elastic)]'
            : 'scale-0 opacity-0',
        )}
      >
        <CheckCircle className="h-10 w-10 text-success" />
      </div>

      {/* Title + subtitle — staggered fade */}
      <div
        className={cn(
          'space-y-2 transition-all duration-500 ease-[var(--ease-out-expo)]',
          stage >= 2 ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4',
        )}
      >
        <h2 className="text-xl font-semibold text-foreground">{title}</h2>
        <p className="text-sm text-foreground-secondary">{subtitle}</p>
      </div>

      {/* CTA button — final fade in */}
      <div
        className={cn(
          'transition-all duration-300 ease-[var(--ease-out-expo)]',
          stage >= 3 ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2',
        )}
      >
        <Button>Continue</Button>
      </div>
    </div>
  );
}
```

### Loading States

Use shimmer skeletons and small spinners:

```tsx
// Skeleton with shimmer
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'rounded-md bg-gradient-to-r from-background-card via-background-hover to-background-card',
        'bg-[length:200%_100%] animate-shimmer',
        className,
      )}
    />
  );
}

// Usage
<Skeleton className="h-4 w-48" />
<Skeleton className="h-10 w-full" />

// Small inline spinner (for button loading states)
export function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={cn('h-4 w-4 animate-spin text-current', className)}
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

// Button with loading state
<Button disabled={loading}>
  {loading ? <><Spinner className="mr-2" /> Saving...</> : 'Save'}
</Button>
```

### Page Transition Wrapper

Wrap page content for smooth entrance when navigating:

```tsx
export function PageTransition({ children }: { children: React.ReactNode }) {
  return (
    <div className="animate-fade-in-up" style={{ animationDuration: '350ms' }}>
      {children}
    </div>
  );
}

// Usage in page components
export function RunsPage() {
  return (
    <PageTransition>
      <PageHeader title="Eval Runs" />
      {/* ... */}
    </PageTransition>
  );
}
```

### Micro-interactions

| Interaction | Implementation |
|-------------|---------------|
| Button hover | `hover:brightness-110 transition-all duration-150` |
| Button press | Scale to `0.97` on mouseDown (see Button Press Animation above) |
| Row hover | `hover:bg-[rgba(255,255,255,0.03)] transition-colors duration-150` |
| Input focus | `focus:border-border-focus focus:ring-1 focus:ring-border-focus transition-colors duration-200` |
| Card hover | `hover:border-border-hover hover:shadow-subtle transition-all duration-200` |
| Toggle switch | `transition-all duration-200 ease-[var(--ease-smooth)]` on both track and thumb |
| Error state | Apply `animate-shake` class, then remove after animation ends |
| Success feedback | Green checkmark with `animate-scale-in-bounce` |
| Tooltip enter | `animate-fade-in` with `duration-150` |
| Dropdown open | `animate-scale-in` on content panel |

### Error Shake Pattern

```tsx
import { useState, useCallback } from 'react';

export function useShake() {
  const [shaking, setShaking] = useState(false);

  const triggerShake = useCallback(() => {
    setShaking(true);
    setTimeout(() => setShaking(false), 400);
  }, []);

  return { shaking, triggerShake };
}

// Usage
const { shaking, triggerShake } = useShake();

<Input
  className={cn('bg-background-input border-border', shaking && 'animate-shake border-error')}
/>

// Trigger on validation failure
if (!isValid) triggerShake();
```

### Collapsible / Accordion Animation

Animate height for expanding/collapsing content:

```tsx
import { useRef, useState } from 'react';

interface CollapsibleProps {
  open: boolean;
  children: React.ReactNode;
}

export function AnimatedCollapsible({ open, children }: CollapsibleProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  return (
    <div
      className="overflow-hidden transition-[max-height,opacity] duration-300 ease-[var(--ease-smooth)]"
      style={{
        maxHeight: open ? contentRef.current?.scrollHeight ?? 1000 : 0,
        opacity: open ? 1 : 0,
      }}
    >
      <div ref={contentRef}>{children}</div>
    </div>
  );
}
```

### Number / Value Count-Up

Animate numbers counting up for dashboard stats:

```tsx
import { useEffect, useState } from 'react';

export function useCountUp(target: number, duration = 600) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (target === 0) { setValue(0); return; }
    const start = performance.now();
    const step = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      // Ease-out quad
      const eased = 1 - (1 - progress) * (1 - progress);
      setValue(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration]);

  return value;
}

// Usage in StatCard
export function StatCard({ label, value }: { label: string; value: number }) {
  const animated = useCountUp(value);
  return (
    <Card className="bg-background-card border-border-muted text-center p-4">
      <div className="text-2xl font-semibold text-foreground">{animated}</div>
      <div className="text-xs font-medium uppercase tracking-wide text-foreground-secondary mt-1">
        {label}
      </div>
    </Card>
  );
}
```

### Animation Composition

Combine multiple animation utilities for richer effects. Always prefer composing simple animations over building complex custom ones:

```tsx
// Combined slide + fade (card entrance)
<div className="animate-fade-in-up" style={{ animationDelay: '100ms' }}>
  <Card>...</Card>
</div>

// Combined scale + pulse ring (success icon)
<div className="animate-scale-in-bounce animate-pulse-ring">
  <CheckCircle className="h-8 w-8 text-success" />
</div>

// Staggered grid entrance
<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
  {stats.map((s, i) => (
    <div key={s.label} className="animate-fade-in-up" style={{ animationDelay: `${i * 75}ms` }}>
      <StatCard {...s} />
    </div>
  ))}
</div>
```

### Animation Don'ts

- **Don't** animate on every render — gate animations behind mount or state changes.
- **Don't** use durations above 800ms for standard UI (loading/success screens are the exception).
- **Don't** animate layout-triggering properties (`width`, `height`, `top`, `left`) — use `transform` and `opacity` only for 60fps performance.
- **Don't** stack multiple heavy animations simultaneously — stagger them.
- **Don't** use `setInterval` for animations — use `requestAnimationFrame` or CSS animations.
- **Don't** forget `prefers-reduced-motion` — always respect user preferences:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Icons

Use **Lucide React** (ships with Shadcn/ui):

```tsx
import { Settings, Play, FileText, Trash2, Plus, Search } from 'lucide-react';

// Inline icon (16px)
<Settings className="h-4 w-4" />

// Nav / action button icon (20px)
<Play className="h-5 w-5" />

// Icon inherits text color via currentColor
<span className="text-foreground-secondary">
  <FileText className="h-4 w-4" />
</span>
```

Icon sizing rules:
- **16px** (`h-4 w-4`): inline with text, table cells, badges
- **20px** (`h-5 w-5`): navigation items, action buttons
- Stroke width: use Lucide defaults (2px). Do not override.

---

## Do's and Don'ts

### Do

- Use Tailwind utility classes for all styling. No inline `style` props.
- Use Shadcn/ui components for all standard UI elements (Button, Input, Card, Table, Dialog, Select, Badge, Progress, etc.).
- Use the theme colors via Tailwind classes (`bg-background-card`, `text-foreground-secondary`, etc.).
- Keep surfaces dark — never use backgrounds lighter than `#1e1e2e` (`bg-background-hover`).
- Use the accent blue sparingly — only for interactive elements and active states.
- Match the 4px spacing grid exactly.
- Use `font-medium` or `font-semibold` for emphasis, never `font-bold` or heavier.
- Compose Shadcn/ui components with `className` overrides for theme customization.
- Use the `cn()` utility from `@/lib/utils` for conditional class merging.

### Don't

- Never write custom CSS when a Tailwind utility exists.
- Never build a custom component when Shadcn/ui already provides one.
- Never use `style={{}}` inline styles in JSX.
- Never use pure white (`#ffffff`) for backgrounds or large text areas.
- Never use pure black (`#000000`) for backgrounds — always add the blue tint.
- Don't use bright/saturated colors for non-status purposes.
- Don't round corners above `rounded-lg` (12px) except `rounded-full` for pills.
- Don't use shadow values lighter than `rgba(0,0,0,0.3)`.
- Don't mix font families — body is `font-sans` (Inter), code is `font-mono`. No exceptions.
- Don't import CSS files in components — all styling goes through Tailwind.
