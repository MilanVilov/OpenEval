# Skill: Frontend Conventions — React + TypeScript Patterns

This skill defines the code conventions, architecture patterns, and best practices for the ai-eval React frontend. All frontend code MUST follow these rules.

---

## TypeScript Rules

- **Strict mode**: `strict: true` in `tsconfig.json`. No exceptions.
- **No `any`**: use `unknown` and narrow with type guards, or define proper types.
- **Prefer `interface` over `type`** for object shapes. Use `type` only for unions, intersections, and mapped types.
- **All function parameters and return types must be typed.** Rely on inference only for inline callbacks.
- **Shared types** live in `frontend/src/types/`, one file per domain (e.g., `config.ts`, `run.ts`, `dataset.ts`).
- **API response types mirror backend Pydantic schemas.** Name them identically where possible.

```ts
// types/config.ts
export interface EvalConfig {
  id: string;
  name: string;
  model: string;
  prompt_template: string;
  comparer_type: string;
  created_at: string;
}

export interface CreateConfigRequest {
  name: string;
  model: string;
  prompt_template: string;
  comparer_type: string;
}
```

---

## React Component Rules

- **Functional components only.** No class components.
- **Named exports only.** No `export default`.
  ```tsx
  // Good
  export function ConfigList() { ... }

  // Bad
  export default function ConfigList() { ... }
  ```
- **One component per file.** Small helper sub-components (used only within that file) are acceptable.
- **File naming:**
  - `PascalCase.tsx` — React components
  - `camelCase.ts` — utilities, hooks, constants, API modules
- **Props interface** defined directly above the component:
  ```tsx
  interface ConfigCardProps {
    config: EvalConfig;
    onDelete: (id: string) => void;
  }

  export function ConfigCard({ config, onDelete }: ConfigCardProps) {
    return ( ... );
  }
  ```
- **Destructure props** in the function signature, not in the body.
- **Keep components under 100 lines.** Extract sub-components or hooks if a component grows larger.

---

## Project Structure

```
frontend/src/
├── api/              # Typed fetch wrappers (one file per resource)
│   ├── client.ts     # Base fetch helper with error handling
│   ├── configs.ts
│   ├── datasets.ts
│   ├── runs.ts
│   └── vectorStores.ts
├── components/       # Shared/reusable components
│   ├── AppLayout.tsx
│   ├── PageHeader.tsx
│   ├── Sidebar.tsx
│   ├── StatusBadge.tsx
│   ├── StatCard.tsx
│   └── ui/           # Shadcn/ui components (auto-generated, do not edit)
├── pages/            # Page-level components (one per route)
│   ├── Dashboard.tsx
│   ├── configs/
│   │   ├── ConfigList.tsx
│   │   ├── ConfigNew.tsx
│   │   ├── ConfigDetail.tsx
│   │   └── ConfigEdit.tsx
│   ├── datasets/
│   │   ├── DatasetList.tsx
│   │   ├── DatasetNew.tsx
│   │   └── DatasetDetail.tsx
│   ├── runs/
│   │   ├── RunList.tsx
│   │   ├── RunNew.tsx
│   │   ├── RunDetail.tsx
│   │   └── RunCompare.tsx
│   └── vector-stores/
│       ├── VectorStoreList.tsx
│       ├── VectorStoreNew.tsx
│       └── VectorStoreDetail.tsx
├── hooks/            # Custom React hooks
│   └── usePolling.ts
├── types/            # TypeScript interfaces
│   ├── config.ts
│   ├── dataset.ts
│   ├── run.ts
│   └── vectorStore.ts
├── lib/              # Utilities
│   └── utils.ts      # cn() helper, formatters
├── globals.css       # Tailwind directives + CSS variables
├── App.tsx           # Router setup
└── main.tsx          # Entry point
```

### Rules

- **`components/ui/`** is managed by Shadcn/ui CLI. Do not manually edit files there.
- **Pages** are the only components that call API functions directly. Shared components receive data via props.
- **Hooks** are prefixed with `use` (e.g., `usePolling.ts`).
- Place new files in the correct directory. Don't dump everything in `components/`.

---

## API Integration Patterns

### Base Fetch Wrapper

```ts
// api/client.ts
const API_BASE = '/api';

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: string,
  ) {
    super(`API error ${status}: ${body}`);
    this.name = 'ApiError';
  }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  return res.json();
}
```

### Per-Resource API Module

One file per backend resource. Functions are thin wrappers around `apiFetch`:

```ts
// api/configs.ts
import { apiFetch } from './client';
import type { EvalConfig, CreateConfigRequest } from '../types/config';

export function listConfigs(): Promise<EvalConfig[]> {
  return apiFetch('/configs');
}

export function getConfig(id: string): Promise<EvalConfig> {
  return apiFetch(`/configs/${id}`);
}

export function createConfig(data: CreateConfigRequest): Promise<EvalConfig> {
  return apiFetch('/configs', { method: 'POST', body: JSON.stringify(data) });
}

export function updateConfig(id: string, data: Partial<CreateConfigRequest>): Promise<EvalConfig> {
  return apiFetch(`/configs/${id}`, { method: 'PUT', body: JSON.stringify(data) });
}

export function deleteConfig(id: string): Promise<void> {
  return apiFetch(`/configs/${id}`, { method: 'DELETE' });
}
```

### File Uploads

For endpoints that accept files (e.g., dataset CSV upload), omit the `Content-Type` header so the browser sets the multipart boundary:

```ts
// api/datasets.ts
export function uploadDataset(name: string, file: File): Promise<Dataset> {
  const form = new FormData();
  form.append('name', name);
  form.append('file', file);
  return apiFetch('/datasets', {
    method: 'POST',
    headers: {},  // Let browser set Content-Type for FormData
    body: form,
  });
}
```

---

## State Management Rules

- **`useState`** for local component state (form fields, toggles, UI flags).
- **`useEffect`** for data fetching on mount and reacting to dependency changes.
- **`useReducer`** for complex local state (forms with many fields, multi-step wizards).
- **NO global state management libraries.** No Redux, no Zustand, no Jotai, no MobX.
- **Lift state up** when sibling components need shared data. Pass it down via props.
- **Polling**: `setInterval` inside `useEffect` with proper cleanup:

```ts
// hooks/usePolling.ts
import { useEffect, useRef } from 'react';

export function usePolling(callback: () => void, intervalMs: number, enabled: boolean): void {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => savedCallback.current(), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, enabled]);
}
```

---

## Data Fetching Pattern

Every page that loads data follows this pattern:

```tsx
import { useState, useEffect } from 'react';
import { listConfigs } from '@/api/configs';
import type { EvalConfig } from '@/types/config';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';

export function ConfigList() {
  const [configs, setConfigs] = useState<EvalConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listConfigs()
      .then(setConfigs)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton className="h-40 w-full" />;

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  return <ConfigTable configs={configs} />;
}
```

### Refresh After Mutation

After a successful create/update/delete, either:
1. Navigate away with `useNavigate()` (preferred for create/delete).
2. Re-fetch the data by calling the list/get function again (preferred for inline updates).

---

## Routing Patterns

```tsx
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppLayout } from '@/components/AppLayout';
import { Dashboard } from '@/pages/Dashboard';
import { ConfigList } from '@/pages/configs/ConfigList';
import { ConfigNew } from '@/pages/configs/ConfigNew';
import { ConfigDetail } from '@/pages/configs/ConfigDetail';
import { ConfigEdit } from '@/pages/configs/ConfigEdit';
// ... other page imports

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/configs" element={<ConfigList />} />
          <Route path="/configs/new" element={<ConfigNew />} />
          <Route path="/configs/:id" element={<ConfigDetail />} />
          <Route path="/configs/:id/edit" element={<ConfigEdit />} />
          <Route path="/datasets" element={<DatasetList />} />
          <Route path="/datasets/new" element={<DatasetNew />} />
          <Route path="/datasets/:id" element={<DatasetDetail />} />
          <Route path="/runs" element={<RunList />} />
          <Route path="/runs/new" element={<RunNew />} />
          <Route path="/runs/:id" element={<RunDetail />} />
          <Route path="/runs/compare" element={<RunCompare />} />
          <Route path="/vector-stores" element={<VectorStoreList />} />
          <Route path="/vector-stores/new" element={<VectorStoreNew />} />
          <Route path="/vector-stores/:id" element={<VectorStoreDetail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

### URL Parameters

Use `useParams()` for route parameters and `useSearchParams()` for query strings:

```tsx
import { useParams } from 'react-router-dom';

export function ConfigDetail() {
  const { id } = useParams<{ id: string }>();
  // fetch config by id...
}
```

---

## Form Patterns

Use controlled components with `useState`. Submit via the API module, navigate on success.

```tsx
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { createConfig } from '@/api/configs';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';

export function ConfigNew() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [promptTemplate, setPromptTemplate] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const config = await createConfig({ name, prompt_template: promptTemplate, model: 'gpt-4o', comparer_type: 'exact_match' });
      navigate(`/configs/${config.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-[600px]">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-2">
        <Label className="text-xs font-medium uppercase tracking-wide text-foreground-secondary">
          Name
        </Label>
        <Input
          value={name}
          onChange={e => setName(e.target.value)}
          required
          className="bg-background-input border-border"
        />
      </div>

      <div className="space-y-2">
        <Label className="text-xs font-medium uppercase tracking-wide text-foreground-secondary">
          Prompt Template
        </Label>
        <Textarea
          value={promptTemplate}
          onChange={e => setPromptTemplate(e.target.value)}
          required
          className="bg-background-input border-border font-mono min-h-[120px]"
        />
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={() => navigate('/configs')}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Creating...' : 'Create Config'}
        </Button>
      </div>
    </form>
  );
}
```

### Validation

- Use HTML5 validation attributes (`required`, `minLength`, `pattern`) as first line of defense.
- Show server-side errors inline above the form or next to the relevant field.
- Do NOT use browser `alert()` for validation messages.

---

## Error Handling

### `ApiError` Class

Defined in `api/client.ts` (see above). Carries HTTP status and response body.

### Error Boundaries

Wrap the app in a React error boundary to catch unexpected render crashes:

```tsx
// components/ErrorBoundary.tsx
import { Component, type ReactNode } from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen items-center justify-center bg-background">
          <div className="text-center">
            <h1 className="text-xl font-semibold text-foreground mb-2">Something went wrong</h1>
            <p className="text-sm text-foreground-secondary">{this.state.error?.message}</p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
```

### Error Display Strategy

- **Inline error states** in components (Alert with `variant="destructive"`). Not global toasts.
- **Loading skeletons** while data is fetching. Not spinners.
- **Empty states** when a list has zero items. Show a message and a CTA button.

---

## Testing

- **E2E tests** with Playwright. Tests live in `tests/e2e/`.
- Test user-visible behavior, not implementation details.
- Each test should be independent and not depend on state from other tests.

---

## Do's and Don'ts

### Do

- Use Shadcn/ui components for all standard UI elements.
- Keep components small: under 100 lines.
- Type everything: props, state, API responses, function parameters.
- Use named exports: `export function MyComponent()`.
- Destructure props in function signatures.
- Use `cn()` from `@/lib/utils` for conditional Tailwind class merging.
- Follow the data-fetching pattern (loading → error → content).
- Use `useNavigate()` for programmatic navigation after mutations.
- Place API calls only in page-level components, pass data down via props.

### Don't

- Don't use `any`. Use `unknown` and narrow, or define proper types.
- Don't add global state management libraries (Redux, Zustand, Jotai, etc.).
- Don't use class components (except ErrorBoundary, which requires it).
- Don't use `export default`.
- Don't write custom CSS when Tailwind utility classes work.
- Don't use inline `style={{}}` props.
- Don't put API calls in shared components — only in pages.
- Don't use `alert()`, `confirm()`, or `prompt()` browser dialogs.
- Don't create barrel files (`index.ts` re-exporting everything).
- Don't install additional UI libraries (Material UI, Ant Design, Chakra, etc.).
