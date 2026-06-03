import type { PaginationParams } from '@/types/pagination';

export function buildPaginationQuery(params: PaginationParams): string {
  const query = new URLSearchParams();
  query.set('page', String(params.page));
  query.set('page_size', String(params.page_size));
  if (params.search?.trim()) {
    query.set('search', params.search.trim());
  }
  return `?${query.toString()}`;
}
