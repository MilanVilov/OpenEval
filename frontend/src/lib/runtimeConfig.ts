declare global {
  interface Window {
    APP_BASE_URL?: string;
  }
}

export function getRouterBasename(): string | undefined {
  return normalizeBasePath(window.APP_BASE_URL ?? getDocumentBasePath() ?? import.meta.env.BASE_URL);
}

export function getApiBaseUrl(): string {
  return `${getRouterBasename() ?? ''}/api`;
}

export function normalizeBasePath(value: string | undefined): string | undefined {
  const base = value?.trim();
  if (!base || base === '/' || base === '.' || base === './') {
    return undefined;
  }

  const path = base.includes('://') ? new URL(base).pathname : base;
  const normalizedPath = path.replace(/^\/+|\/+$/g, '');
  if (!normalizedPath) {
    return undefined;
  }
  return `/${normalizedPath}`;
}

function getDocumentBasePath(): string | undefined {
  const baseElement = document.querySelector('base');
  return baseElement?.getAttribute('href') ?? undefined;
}
