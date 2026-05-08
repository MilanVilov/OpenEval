export type PaginationMode = 'none' | 'page' | 'offset' | 'next_token';

export interface JsonExample {
  label: string;
  value: string;
}

export const QUERY_PARAMS_EXAMPLE = '{\n  "category": "dessert",\n  "include": "reviews"\n}';

export const QUERY_PARAMS_EXAMPLES: JsonExample[] = [
  {
    label: 'Filtering',
    value: QUERY_PARAMS_EXAMPLE,
  },
  {
    label: 'Sorting and includes',
    value: '{\n  "sortBy": "createdAt",\n  "order": "desc",\n  "include": "reviews"\n}',
  },
];

export const PUBLIC_HEADERS_EXAMPLE = '{\n  "Accept": "application/json",\n  "User-Agent": "OpenEval Importer"\n}';

export const PUBLIC_HEADERS_EXAMPLES: JsonExample[] = [
  {
    label: 'Standard JSON request',
    value: PUBLIC_HEADERS_EXAMPLE,
  },
  {
    label: 'Versioned API',
    value: '{\n  "Accept": "application/json",\n  "X-Api-Version": "2026-05-01"\n}',
  },
];

export const SECRET_HEADERS_EXAMPLE = '{\n  "X-Api-Key": "secret-key-value"\n}';

export const SECRET_HEADERS_DESCRIPTION =
  'Use this for API keys and other sensitive header values. Secret headers are encrypted before they are stored and only their names are shown again in the UI.';

export const SECRET_HEADERS_EXAMPLES: JsonExample[] = [
  {
    label: 'API key',
    value: SECRET_HEADERS_EXAMPLE,
  },
  {
    label: 'Client credentials',
    value: '{\n  "X-Client-Id": "client_123",\n  "X-Client-Secret": "super-secret-value"\n}',
  },
];

export const PAGINATION_CONFIG_EXAMPLES: JsonExample[] = [
  {
    label: 'None',
    value: '{}',
  },
  {
    label: 'Page',
    value: '{\n  "page_param": "page",\n  "page_size_param": "limit",\n  "page_size": 25,\n  "start_page": 1,\n  "has_more_path": "$.meta.has_more"\n}',
  },
  {
    label: 'Offset + limit',
    value: '{\n  "offset_param": "skip",\n  "limit_param": "limit",\n  "page_size": 30,\n  "start_offset": 0\n}',
  },
  {
    label: 'Next token',
    value: '{\n  "token_param": "cursor",\n  "response_token_path": "$.nextCursor"\n}',
  },
  {
    label: 'Send pagination in POST body',
    value: '{\n  "offset_param": "skip",\n  "limit_param": "limit",\n  "page_size": 30,\n  "placement": "body"\n}',
  },
];

export function buildPaginationPlaceholder(paginationMode: PaginationMode): string {
  if (paginationMode === 'page') {
    return '{\n  "page_param": "page",\n  "page_size_param": "limit",\n  "page_size": 25,\n  "start_page": 1,\n  "has_more_path": "$.meta.has_more"\n}';
  }
  if (paginationMode === 'offset') {
    return '{\n  "offset_param": "skip",\n  "limit_param": "limit",\n  "page_size": 30,\n  "start_offset": 0\n}';
  }
  if (paginationMode === 'next_token') {
    return '{\n  "token_param": "cursor",\n  "response_token_path": "$.nextCursor"\n}';
  }
  return '{}';
}
