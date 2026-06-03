import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';

interface ListControlsProps {
  page: number;
  pageSize: number;
  pages: number;
  total: number;
  itemLabel: string;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}

interface ListSearchProps {
  search: string;
  itemLabel: string;
  onSearchChange: (value: string) => void;
}

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

export function ListSearch({ search, itemLabel, onSearchChange }: ListSearchProps) {
  return (
    <Input
      type="search"
      value={search}
      onChange={(event) => onSearchChange(event.target.value)}
      placeholder={`Search ${itemLabel}`}
      aria-label={`Search ${itemLabel}`}
      className="mb-4 max-w-sm"
    />
  );
}

export function ListPagination({
  page,
  pageSize,
  pages,
  total,
  itemLabel,
  onPageChange,
  onPageSizeChange,
}: ListControlsProps) {
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <div className="mt-4 flex flex-col gap-3 text-xs text-foreground-secondary sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-3">
        <span>{start}-{end} of {total} {itemLabel}</span>
        <label className="flex items-center gap-2">
          Per page
          <Select
            value={String(pageSize)}
            onChange={(event) => onPageSizeChange(Number(event.target.value))}
            className="w-24"
          >
            {PAGE_SIZE_OPTIONS.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </Select>
        </label>
      </div>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span>Page {page} of {pages}</span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
          aria-label="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
