import { ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';

interface ListControlsProps {
  search: string;
  page: number;
  pageSize: number;
  pages: number;
  total: number;
  itemLabel: string;
  onSearchChange: (value: string) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

export function ListControls({
  search,
  page,
  pageSize,
  pages,
  total,
  itemLabel,
  onSearchChange,
  onPageChange,
  onPageSizeChange,
}: ListControlsProps) {
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <div className="mb-4 flex flex-col gap-3 rounded border border-border bg-background-secondary p-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-foreground-disabled" />
          <Input
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder={`Search ${itemLabel}`}
            className="pl-9"
          />
        </div>
        <label className="flex items-center gap-2 text-xs text-foreground-secondary">
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
      <div className="flex flex-col gap-2 text-xs text-foreground-secondary sm:flex-row sm:items-center sm:justify-between">
        <span>{start}-{end} of {total} {itemLabel}</span>
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
    </div>
  );
}
