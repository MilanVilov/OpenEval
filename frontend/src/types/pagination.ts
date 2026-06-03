export interface PaginationParams {
  page: number;
  page_size: number;
  search?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  search: string | null;
}
