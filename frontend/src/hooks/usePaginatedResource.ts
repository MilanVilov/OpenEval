import { useCallback, useEffect, useState } from 'react';
import type { PaginatedResponse, PaginationParams } from '@/types/pagination';

interface UsePaginatedResourceResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
  search: string;
  loading: boolean;
  error: string | null;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
  setSearch: (search: string) => void;
  refresh: () => Promise<void>;
}

export function usePaginatedResource<T>(
  loadPage: (params: PaginationParams) => Promise<PaginatedResponse<T>>,
): UsePaginatedResourceResult<T> {
  const [items, setItems] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSizeValue, setPageSizeValue] = useState(10);
  const [pages, setPages] = useState(1);
  const [searchValue, setSearchValue] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await loadPage({ page, page_size: pageSizeValue, search: searchValue });
      setItems(result.items);
      setTotal(result.total);
      setPages(result.pages);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load list');
    } finally {
      setLoading(false);
    }
  }, [loadPage, page, pageSizeValue, searchValue]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  function setPageSize(pageSize: number): void {
    setPageSizeValue(pageSize);
    setPage(1);
  }

  function setSearch(search: string): void {
    setSearchValue(search);
    setPage(1);
  }

  return {
    items,
    total,
    page,
    pageSize: pageSizeValue,
    pages,
    search: searchValue,
    loading,
    error,
    setPage,
    setPageSize,
    setSearch,
    refresh,
  };
}
