const API_BASE = '/api';

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string) {
    super(formatApiErrorMessage(status, body));
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

interface ApiErrorPayload {
  detail?: unknown;
  error?: unknown;
  message?: unknown;
  msg?: unknown;
}

export function formatApiErrorMessage(status: number, body: string): string {
  const payload = parseJson(body);
  const message = extractApiErrorMessage(payload);
  if (message) {
    return message;
  }

  const trimmedBody = body.trim();
  if (trimmedBody) {
    return trimmedBody;
  }

  return `Request failed with status ${status}.`;
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

export async function downloadFile(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }

  const blob = await res.blob();
  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = getDownloadFilename(res.headers.get('Content-Disposition'));
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(objectUrl);
}

function getDownloadFilename(contentDisposition: string | null): string {
  if (!contentDisposition) {
    return 'export.csv';
  }

  const match = contentDisposition.match(/filename="([^"]+)"/i);
  if (!match) {
    return 'export.csv';
  }

  return match[1];
}

function parseJson(body: string): unknown | null {
  try {
    return JSON.parse(body) as unknown;
  } catch {
    return null;
  }
}

function extractApiErrorMessage(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed || null;
  }

  if (Array.isArray(value)) {
    const messages = value
      .map((item) => formatValidationMessage(item) ?? extractApiErrorMessage(item))
      .filter((message): message is string => Boolean(message));

    if (messages.length === 0) {
      return null;
    }

    return [...new Set(messages)].join(' ');
  }

  if (!isApiErrorPayload(value)) {
    return null;
  }

  return (
    extractApiErrorMessage(value.detail) ??
    extractApiErrorMessage(value.message) ??
    extractApiErrorMessage(value.error) ??
    extractApiErrorMessage(value.msg)
  );
}

function formatValidationMessage(value: unknown): string | null {
  if (!isApiErrorPayload(value) || typeof value.msg !== 'string') {
    return null;
  }

  const location = formatErrorLocation(value.detail ?? value.loc);
  return location ? `${location}: ${value.msg}` : value.msg;
}

function formatErrorLocation(value: unknown): string | null {
  if (!Array.isArray(value)) {
    return null;
  }

  const segments = value
    .filter((segment): segment is string | number => typeof segment === 'string' || typeof segment === 'number')
    .map(String)
    .filter((segment) => !['body', 'query', 'path'].includes(segment));

  if (segments.length === 0) {
    return null;
  }

  return segments
    .map((segment) => segment.replace(/[_-]+/g, ' '))
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' > ');
}

function isApiErrorPayload(value: unknown): value is ApiErrorPayload & { loc?: unknown } {
  return typeof value === 'object' && value !== null;
}
