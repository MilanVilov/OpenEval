import { useState } from 'react';
import { Link } from 'react-router-dom';
import { exportRun, listRunsPage } from '@/api/runs';
import type { EvalRun } from '@/types/run';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { StatusBadge } from '@/components/StatusBadge';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card } from '@/components/ui/card';
import { Download, Plus } from 'lucide-react';
import { formatDate, formatPercent, formatLatency, formatTokens } from '@/lib/utils';
import { ListPagination, ListSearch } from '@/components/ListControls';
import { usePaginatedResource } from '@/hooks/usePaginatedResource';

export function RunList() {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const {
    items: runs,
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
  } = usePaginatedResource<EvalRun>(listRunsPage);

  async function handleExport(runId: string): Promise<void> {
    setDownloadingId(runId);
    setActionError(null);
    try {
      await exportRun(runId);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to export evaluation');
    } finally {
      setDownloadingId(null);
    }
  }

  if (loading && runs.length === 0 && total === 0 && !search) return <LoadingSkeleton rows={5} />;
  if (error) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>;

  return (
    <PageTransition>
      <PageHeader
        title="Evaluation Runs"
        description="View and manage evaluation runs"
        action={
          <Link to="/runs/new">
            <Button size="sm"><Plus className="mr-2 h-4 w-4" />New Run</Button>
          </Link>
        }
      />

      <ListSearch
        search={search}
        itemLabel="runs"
        onSearchChange={setSearch}
      />
      {actionError && (
        <Alert variant="destructive" className="mb-4 animate-fade-in">
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      )}

      {runs.length === 0 ? (
        <Card className="p-12 text-center animate-scale-in">
          <p className="text-foreground-secondary text-base">
            {search ? 'No runs match your search.' : 'No runs yet.'}
          </p>
          {!search && (
            <Link to="/runs/new">
              <Button className="mt-4" size="sm">Start your first run</Button>
            </Link>
          )}
        </Card>
      ) : (
        <div className="animate-fade-in">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Config</TableHead>
                <TableHead>Dataset</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Accuracy</TableHead>
                <TableHead>Latency</TableHead>
                <TableHead>Tokens (in/out)</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="w-28 text-right">Export</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.map((run, idx) => (
                <TableRow
                  key={run.id}
                  className="animate-fade-in-up hover:bg-background-hover transition-colors duration-150"
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <TableCell>
                    <Link to={`/runs/${run.id}`} className="text-foreground-link hover:underline">
                      {run.config_name ?? 'Unknown'}
                    </Link>
                  </TableCell>
                  <TableCell>{run.dataset_name ?? 'Unknown'}</TableCell>
                  <TableCell><StatusBadge status={run.status} /></TableCell>
                  <TableCell className="tabular-nums">{run.summary ? formatPercent(run.summary.accuracy) : '—'}</TableCell>
                  <TableCell className="tabular-nums">{run.summary?.avg_latency_ms != null ? formatLatency(run.summary.avg_latency_ms) : '—'}</TableCell>
                  <TableCell className="tabular-nums">{run.summary?.avg_input_tokens != null ? `${formatTokens(run.summary.avg_input_tokens)} / ${formatTokens(run.summary.avg_output_tokens)}` : '—'}</TableCell>
                  <TableCell>{formatDate(run.created_at)}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={downloadingId === run.id}
                      onClick={() => void handleExport(run.id)}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      {downloadingId === run.id ? 'Exporting...' : 'CSV'}
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
        itemLabel="runs"
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />
    </PageTransition>
  );
}
