import { useState } from 'react';
import { Link } from 'react-router-dom';
import { exportDataset, listDatasetsPage } from '@/api/datasets';
import type { Dataset } from '@/types/dataset';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Download, Plus } from 'lucide-react';
import { formatDate } from '@/lib/utils';
import { ListPagination, ListSearch } from '@/components/ListControls';
import { usePaginatedResource } from '@/hooks/usePaginatedResource';

export function DatasetList() {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const {
    items: datasets,
    total,
    page,
    pageSize,
    pages,
    search,
    loading,
    error,
    setPage,
    setPageSize,
    setSearch,
  } = usePaginatedResource<Dataset>(listDatasetsPage);

  async function handleExport(datasetId: string): Promise<void> {
    setDownloadingId(datasetId);
    setActionError(null);
    try {
      await exportDataset(datasetId);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to export dataset');
    } finally {
      setDownloadingId(null);
    }
  }

  if (loading && datasets.length === 0 && total === 0 && !search) return <LoadingSkeleton rows={4} />;
  if (error) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>;

  return (
    <PageTransition>
      <PageHeader
        title="Datasets"
        description="Manage evaluation datasets"
        action={
          <Link to="/datasets/new">
            <Button size="sm"><Plus className="mr-2 h-4 w-4" />Upload Dataset</Button>
          </Link>
        }
      />

      <ListSearch
        search={search}
        itemLabel="datasets"
        onSearchChange={setSearch}
      />
      {actionError && (
        <Alert variant="destructive" className="mb-4 animate-fade-in">
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      )}

      {datasets.length === 0 ? (
        <Card className="p-12 text-center animate-scale-in">
          <p className="text-foreground-secondary text-base">
            {search ? 'No datasets match your search.' : 'No datasets yet.'}
          </p>
          {!search && (
            <Link to="/datasets/new">
              <Button className="mt-4" size="sm">Upload your first dataset</Button>
            </Link>
          )}
        </Card>
      ) : (
        <div className="animate-fade-in">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Rows</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="w-24 text-right">Export</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {datasets.map((ds, idx) => (
                <TableRow
                  key={ds.id}
                  className="animate-fade-in-up hover:bg-background-hover transition-colors duration-150"
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Link to={`/datasets/${ds.id}`} className="text-foreground-link hover:underline">{ds.name}</Link>
                      {ds.has_import_source ? <Badge variant="info">Imported</Badge> : null}
                    </div>
                  </TableCell>
                  <TableCell className="tabular-nums">{ds.row_count}</TableCell>
                  <TableCell>{formatDate(ds.created_at)}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={downloadingId === ds.id}
                      onClick={() => void handleExport(ds.id)}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      {downloadingId === ds.id ? 'Exporting...' : 'CSV'}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <ListPagination
        page={page}
        pageSize={pageSize}
        pages={pages}
        total={total}
        itemLabel="datasets"
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />
    </PageTransition>
  );
}
