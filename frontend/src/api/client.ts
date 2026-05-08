import { getApiBaseUrl } from '@/lib/runtimeConfig';

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string) {
    super(`API error ${status}: ${body}`);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${getApiBaseUrl()}${path}`, {
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
  const res = await fetch(`${getApiBaseUrl()}${path}`);
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
