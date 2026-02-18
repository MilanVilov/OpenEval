import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getRun, getRunProgress, getRunResults, deleteRun } from '@/api/runs';
import type { EvalRun, RunProgress, EvalResult } from '@/types/run';
import { usePolling } from '@/hooks/usePolling';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { StatusBadge } from '@/components/StatusBadge';
import { StatCard } from '@/components/StatCard';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { formatDate, formatPercent } from '@/lib/utils';
import { Trash2 } from 'lucide-react';

export function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<EvalRun | null>(null);
  const [progress, setProgress] = useState<RunProgress | null>(null);
  const [results, setResults] = useState<EvalResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFailuresOnly, setShowFailuresOnly] = useState(false);

  useEffect(() => {
    if (!id) return;
    Promise.all([getRun(id), getRunResults(id)])
      .then(([r, res]) => {
        setRun(r);
        setResults(res);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const isRunning = run?.status === 'running' || run?.status === 'pending';

  const pollCallback = useCallback(async () => {
    if (!id) return;
    const [updatedRun, prog, res] = await Promise.all([
      getRun(id),
      getRunProgress(id),
      getRunResults(id),
    ]);
    setRun(updatedRun);
    setProgress(prog);
    setResults(res);
  }, [id]);

  usePolling(pollCallback, 2000, isRunning);

  async function handleDelete() {
    if (!id || !confirm('Delete this run?')) return;
    await deleteRun(id);
    navigate('/runs');
  }

  if (loading) return <Skeleton className="h-60 w-full" />;
  if (error) return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;
  if (!run) return <Alert variant="destructive"><AlertDescription>Run not found</AlertDescription></Alert>;

  const filteredResults = showFailuresOnly ? results.filter((r) => !r.passed) : results;
  const progressPct = progress ? Math.round((progress.progress / Math.max(progress.total_rows, 1)) * 100) : 0;

  return (
    <div>
      <PageHeader
        title={`Run: ${run.config_name ?? 'Unknown'}`}
        description={`Dataset: ${run.dataset_name ?? 'Unknown'} · ${formatDate(run.created_at)}`}
        action={
          <div className="flex items-center gap-2">
            <StatusBadge status={run.status} />
            <Button variant="destructive" size="sm" onClick={handleDelete}>
              <Trash2 className="mr-2 h-4 w-4" />Delete
            </Button>
          </div>
        }
      />

      {isRunning && progress && (
        <Card className="mb-4">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-foreground-secondary">Progress</span>
              <span className="text-sm font-medium">{progress.progress}/{progress.total_rows}</span>
            </div>
            <Progress value={progressPct} />
            <div className="flex gap-4 mt-2 text-xs text-foreground-secondary">
              <span>Status: {progress.status}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {run.summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard label="Accuracy" value={formatPercent(run.summary.accuracy)} />
          <StatCard label="Total" value={String(run.summary.total)} />
          <StatCard label="Passed" value={String(run.summary.passed)} />
          <StatCard label="Failed" value={String(run.summary.failed)} />
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Results</CardTitle>
            <Button
              variant={showFailuresOnly ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowFailuresOnly(!showFailuresOnly)}
            >
              {showFailuresOnly ? 'Show All' : 'Failures Only'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {filteredResults.length === 0 ? (
            <p className="text-foreground-secondary text-sm py-4">
              {results.length === 0 ? 'No results yet' : 'No failures found'}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">#</TableHead>
                    <TableHead>Input</TableHead>
                    <TableHead>Expected</TableHead>
                    <TableHead>Actual</TableHead>
                    <TableHead className="w-20">Match</TableHead>
                    <TableHead className="w-20">Score</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredResults.map((result) => (
                    <TableRow key={result.id}>
                      <TableCell>{result.row_index}</TableCell>
                      <TableCell className="max-w-[200px] truncate">{result.input_data}</TableCell>
                      <TableCell className="max-w-[200px] truncate">{result.expected_output}</TableCell>
                      <TableCell className="max-w-[200px] truncate">{result.actual_output}</TableCell>
                      <TableCell>
                        <Badge variant={result.passed ? 'success' : 'error'}>
                          {result.passed ? 'Pass' : 'Fail'}
                        </Badge>
                      </TableCell>
                      <TableCell>{result.comparer_score != null ? result.comparer_score.toFixed(2) : '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
