import { useState, type FormEvent, type ReactNode } from 'react';
import type { DataSourceDetail, DataSourcePayload, JsonValue } from '@/types/dataSource';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Spinner } from '@/components/Spinner';
import {
  buildPaginationPlaceholder,
  PAGINATION_CONFIG_EXAMPLES,
  PUBLIC_HEADERS_EXAMPLE,
  PUBLIC_HEADERS_EXAMPLES,
  QUERY_PARAMS_EXAMPLE,
  QUERY_PARAMS_EXAMPLES,
  SECRET_HEADERS_DESCRIPTION,
  SECRET_HEADERS_EXAMPLE,
  SECRET_HEADERS_EXAMPLES,
} from './dataSourceForm.examples';

interface DataSourceFormProps {
  mode: 'create' | 'edit';
  initial?: DataSourceDetail | null;
  error?: string | null;
  submitting: boolean;
  submitLabel: string;
  onSubmit: (payload: Partial<DataSourcePayload>) => Promise<void> | void;
  onCancel?: () => void;
}

export function DataSourceForm({
  mode,
  initial,
  error,
  submitting,
  submitLabel,
  onSubmit,
  onCancel,
}: DataSourceFormProps) {
  const [name, setName] = useState(() => initial?.name ?? '');
  const [url, setUrl] = useState(() => initial?.url ?? '');
  const [method, setMethod] = useState<'GET' | 'POST'>(() => (initial?.method === 'POST' ? 'POST' : 'GET'));
  const [authType, setAuthType] = useState<'none' | 'bearer' | 'basic' | 'header_set'>(() =>
    initial?.auth_type === 'bearer'
      ? 'bearer'
      : initial?.auth_type === 'basic'
        ? 'basic'
        : initial?.auth_type === 'header_set'
          ? 'header_set'
          : 'none',
  );
  const [paginationMode, setPaginationMode] = useState<'none' | 'page' | 'offset' | 'next_token'>(() =>
    initial?.pagination_mode === 'page'
      ? 'page'
      : initial?.pagination_mode === 'offset'
        ? 'offset'
        : initial?.pagination_mode === 'next_token'
          ? 'next_token'
          : 'none',
  );
  const [queryParamsText, setQueryParamsText] = useState(() => JSON.stringify(initial?.query_params ?? {}, null, 2));
  const [headersText, setHeadersText] = useState(() => JSON.stringify(initial?.headers ?? {}, null, 2));
  const [requestBodyText, setRequestBodyText] = useState(() =>
    initial?.request_body ? JSON.stringify(initial.request_body, null, 2) : '',
  );
  const [secretHeadersText, setSecretHeadersText] = useState('');
  const [paginationConfigText, setPaginationConfigText] = useState(() =>
    JSON.stringify(initial?.pagination_config ?? {}, null, 2),
  );
  const [bearerToken, setBearerToken] = useState('');
  const [basicUsername, setBasicUsername] = useState('');
  const [basicPassword, setBasicPassword] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const paginationConfigPlaceholder = buildPaginationPlaceholder(paginationMode);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      const payload: Partial<DataSourcePayload> = {
        name: name.trim(),
        url: url.trim(),
        method,
        auth_type: authType,
        query_params: parseStringMap(queryParamsText, 'Query params'),
        headers: parseStringMap(headersText, 'Headers'),
        request_body: method === 'POST' ? parseOptionalJson(requestBodyText) : null,
        pagination_mode: paginationMode,
        pagination_config: parseJsonObject(paginationConfigText, 'Pagination config'),
      };

      if (mode === 'create' || bearerToken.trim() !== '') {
        payload.bearer_token = bearerToken.trim();
      }
      if (mode === 'create' || basicUsername.trim() !== '') {
        payload.basic_username = basicUsername.trim();
      }
      if (mode === 'create' || basicPassword.trim() !== '') {
        payload.basic_password = basicPassword.trim();
      }
      if (mode === 'create' || secretHeadersText.trim() !== '') {
        payload.secret_headers = parseStringMap(secretHeadersText || '{}', 'Secret headers');
      }

      await onSubmit(payload);
    } catch (submitError) {
      setFormError(submitError instanceof Error ? submitError.message : 'Invalid form values');
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {(error || formError) && (
        <Alert variant="destructive">
          <AlertDescription>{error ?? formError}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label>Name</Label>
          <Input value={name} onChange={(event) => setName(event.target.value)} required placeholder="Support API" />
        </div>
        <div className="space-y-2">
          <Label>URL</Label>
          <Input value={url} onChange={(event) => setUrl(event.target.value)} required placeholder="https://api.example.com/items" />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <Label>Method</Label>
          <Select value={method} onChange={(event) => setMethod(event.target.value === 'POST' ? 'POST' : 'GET')}>
            <option value="GET">GET</option>
            <option value="POST">POST</option>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Auth</Label>
          <Select
            value={authType}
            onChange={(event) =>
              setAuthType(
                event.target.value === 'bearer'
                  ? 'bearer'
                  : event.target.value === 'basic'
                    ? 'basic'
                    : event.target.value === 'header_set'
                      ? 'header_set'
                      : 'none',
              )
            }
          >
            <option value="none">None</option>
            <option value="bearer">Bearer token</option>
            <option value="basic">Basic auth</option>
            <option value="header_set">Header set</option>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Pagination</Label>
          <Select
            value={paginationMode}
            onChange={(event) =>
              setPaginationMode(
                event.target.value === 'page'
                  ? 'page'
                  : event.target.value === 'offset'
                    ? 'offset'
                    : event.target.value === 'next_token'
                      ? 'next_token'
                      : 'none',
              )
            }
          >
            <option value="none">None</option>
            <option value="page">Page</option>
            <option value="offset">Offset + limit</option>
            <option value="next_token">Next token</option>
          </Select>
        </div>
      </div>

      {(mode === 'edit' && initial?.has_secret_credentials) && (
        <p className="text-xs text-foreground-secondary">
          Leave secret fields blank to keep the existing encrypted credentials.
        </p>
      )}

      {authType === 'bearer' && (
        <div className="space-y-2">
          <Label>Bearer Token</Label>
          <Input
            type="password"
            value={bearerToken}
            onChange={(event) => setBearerToken(event.target.value)}
            placeholder={mode === 'edit' ? 'Leave blank to keep current token' : 'sk-...'}
          />
        </div>
      )}

      {authType === 'basic' && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Basic Username</Label>
            <Input
              value={basicUsername}
              onChange={(event) => setBasicUsername(event.target.value)}
              placeholder={mode === 'edit' ? 'Leave blank to keep current username' : 'api-user'}
            />
          </div>
          <div className="space-y-2">
            <Label>Basic Password</Label>
            <Input
              type="password"
              value={basicPassword}
              onChange={(event) => setBasicPassword(event.target.value)}
              placeholder={mode === 'edit' ? 'Leave blank to keep current password' : 'password'}
            />
          </div>
        </div>
      )}

      <JsonField
        label="Query Params JSON"
        value={queryParamsText}
        onChange={setQueryParamsText}
        placeholder={QUERY_PARAMS_EXAMPLE}
        helperText={
          <JsonExamples
            title="Query param examples"
            description="Use this for non-secret URL parameters that should always be sent with the request."
            examples={QUERY_PARAMS_EXAMPLES}
          />
        }
      />
      <JsonField
        label="Public Headers JSON"
        value={headersText}
        onChange={setHeadersText}
        placeholder={PUBLIC_HEADERS_EXAMPLE}
        helperText={
          <JsonExamples
            title="Public header examples"
            description="Use this for non-secret headers that are safe to show again in the UI."
            examples={PUBLIC_HEADERS_EXAMPLES}
          />
        }
      />
      <JsonField
        label="Secret Headers JSON"
        value={secretHeadersText}
        onChange={setSecretHeadersText}
        placeholder={SECRET_HEADERS_EXAMPLE}
        helperText={
          <JsonExamples
            title="Secret header examples"
            description={SECRET_HEADERS_DESCRIPTION}
            examples={SECRET_HEADERS_EXAMPLES}
          />
        }
      />
      {initial?.secret_header_names.length ? (
        <p className="text-xs text-foreground-secondary">
          Stored secret header names: {initial.secret_header_names.join(', ')}
        </p>
      ) : null}
      {method === 'POST' && (
        <JsonField
          label="Request Body JSON"
          value={requestBodyText}
          onChange={setRequestBodyText}
          placeholder='{\n  "limit": 25\n}'
        />
      )}
      <JsonField
        label="Pagination Config JSON"
        value={paginationConfigText}
        onChange={setPaginationConfigText}
        placeholder={paginationConfigPlaceholder}
        helperText={
          <JsonExamples
            title="Pagination config examples"
            description="Choose the pagination mode above, then use the matching config. The examples below cover all supported modes."
            examples={PAGINATION_CONFIG_EXAMPLES}
          />
        }
      />

      <div className="flex justify-end gap-2 pt-2">
        {onCancel ? <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button> : null}
        <Button type="submit" disabled={submitting}>
          {submitting ? <Spinner className="mr-2" /> : null}
          {submitting ? 'Saving...' : submitLabel}
        </Button>
      </div>
    </form>
  );
}

interface JsonFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  helperText?: ReactNode;
}

function JsonField({ label, value, onChange, placeholder, helperText }: JsonFieldProps) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={6}
        placeholder={placeholder}
        className="font-mono text-xs"
      />
      {helperText}
    </div>
  );
}

interface JsonExamplesProps {
  title: string;
  description: string;
  examples: Array<{
    label: string;
    value: string;
  }>;
}

function JsonExamples({ title, description, examples }: JsonExamplesProps) {
  return (
    <details className="rounded-md border border-border bg-background-secondary/60 px-4 py-3">
      <summary className="cursor-pointer text-xs font-medium text-foreground-secondary">
        {title}
      </summary>
      <div className="mt-3 space-y-3">
        <p className="text-xs text-foreground-secondary">{description}</p>
        {examples.map((example) => (
          <div key={example.label} className="space-y-1">
            <p className="text-xs font-medium text-foreground">{example.label}</p>
            <pre className="overflow-x-auto rounded-md border border-border bg-background px-3 py-2 font-mono text-xs text-foreground-secondary">
              {example.value}
            </pre>
          </div>
        ))}
      </div>
    </details>
  );
}


function parseStringMap(text: string, label: string): Record<string, string> {
  const parsed = parseJsonObject(text, label);
  return Object.fromEntries(
    Object.entries(parsed).map(([key, value]) => [key, String(value)]),
  );
}

function parseJsonObject(text: string, label: string): Record<string, JsonValue> {
  const trimmed = text.trim();
  if (!trimmed) {
    return {};
  }
  const parsed = JSON.parse(trimmed) as JsonValue;
  if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
    throw new Error(`${label} must be a JSON object`);
  }
  return parsed as Record<string, JsonValue>;
}

function parseOptionalJson(text: string): JsonValue | null {
  const trimmed = text.trim();
  if (!trimmed) {
    return null;
  }
  return JSON.parse(trimmed) as JsonValue;
}
