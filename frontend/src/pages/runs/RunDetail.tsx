import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { deleteRun, exportRun, getRun, getRunProgress, getRunResults } from '@/api/runs';
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
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
import { formatDate, formatPercent, formatTokens } from '@/lib/utils';
import { Download, Trash2 } from 'lucide-react';

export function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<EvalRun | null>(null);
  const [progress, setProgress] = useState<RunProgress | null>(null);
  const [results, setResults] = useState<EvalResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFailuresOnly, setShowFailuresOnly] = useState(false);
  const [exporting, setExporting] = useState(false);

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

  async function handleExport() {
    if (!id) return;
    setExporting(true);
    setError(null);
    try {
      await exportRun(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to export evaluation');
    } finally {
      setExporting(false);
    }
  }

  if (loading) return <LoadingSkeleton rows={6} />;
  if (error) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>;
  if (!run) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>Run not found</AlertDescription></Alert>;

  const filteredResults = showFailuresOnly ? results.filter((r) => !r.passed) : results;
  const progressPct = progress ? Math.round((progress.progress / Math.max(progress.total_rows, 1)) * 100) : 0;

  // Extract unique comparer names from results for dynamic columns
  const comparerNames = Array.from(
    new Set(
      results.flatMap((r) =>
        r.comparer_details && typeof r.comparer_details === 'object'
          ? Object.keys(r.comparer_details)
          : []
      )
    )
  );

  return (
    <PageTransition>
      <PageHeader
        title={`Run: ${run.config_name ?? 'Unknown'}`}
        description={`Dataset: ${run.dataset_name ?? 'Unknown'} · ${formatDate(run.created_at)}`}
        action={
          <div className="flex items-center gap-2">
            <StatusBadge status={run.status} />
            <Button variant="outline" size="sm" onClick={() => void handleExport()} disabled={exporting}>
              <Download className="mr-2 h-4 w-4" />
              {exporting ? 'Exporting...' : 'Export CSV'}
            </Button>
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
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-6 animate-fade-in">
          <StatCard label="Accuracy" value={formatPercent(run.summary.accuracy)} />
          <StatCard label="Total" value={String(run.summary.total)} />
          <StatCard label="Passed" value={String(run.summary.passed)} />
          <StatCard label="Failed" value={String(run.summary.failed)} />
          <StatCard label="Avg Latency" value={`${run.summary.avg_latency_ms}ms`} />
          <StatCard label="Avg Input Tokens" value={formatTokens(run.summary.avg_input_tokens ?? 0)} />
          <StatCard label="Avg Output Tokens" value={formatTokens(run.summary.avg_output_tokens ?? 0)} />
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Results</CardTitle>
              <p className="mt-1 text-xs text-foreground-secondary">
                CSV export includes row outputs, grader reasoning, latency, token usage, and raw comparer details.
              </p>
            </div>
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
                    {comparerNames.length > 0 ? (
                      comparerNames.map((name) => (
                        <TableHead key={name} className="w-24 text-center">{name}</TableHead>
                      ))
                    ) : (
                      <TableHead className="w-20">Match</TableHead>
                    )}
                    <TableHead className="w-20">Score</TableHead>
                    <TableHead className="w-24">Latency</TableHead>
                    <TableHead className="w-28">Tokens (in/out)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredResults.map((result) => (
                    <TableRow key={result.id}>
                      <TableCell>{result.row_index}</TableCell>
                      <TableCell className="min-w-[200px] max-w-[400px] whitespace-pre-wrap break-words">{result.input_data}</TableCell>
                      <TableCell className="min-w-[200px] max-w-[400px] whitespace-pre-wrap break-words">{result.expected_output}</TableCell>
                      <TableCell className="min-w-[200px] max-w-[400px] whitespace-pre-wrap break-words">
                        {result.actual_output ?? (
                          result.error ? (
                            <span className="text-red-400 text-xs">{result.error}</span>
                          ) : '—'
                        )}
                      </TableCell>
                      {comparerNames.length > 0 ? (
                        comparerNames.map((name) => {
                          const detail = result.comparer_details?.[name] as Record<string, unknown> | undefined;
                          if (!detail) return <TableCell key={name} className="text-center">—</TableCell>;
                          const p = detail.passed as boolean | undefined;
                          return (
                            <TableCell key={name} className="text-center" title={JSON.stringify(detail, null, 2)}>
                              <Badge variant={p ? 'success' : 'error'}>
                                {p ? 'Pass' : 'Fail'}
                              </Badge>
                            </TableCell>
                          );
                        })
                      ) : (
                        <TableCell>
                          <Badge variant={result.passed ? 'success' : 'error'}>
                            {result.passed ? 'Pass' : 'Fail'}
                          </Badge>
                        </TableCell>
                      )}
                      <TableCell>{result.comparer_score != null ? result.comparer_score.toFixed(2) : '—'}</TableCell>
                      <TableCell>{result.latency_ms != null ? `${result.latency_ms}ms` : '—'}</TableCell>
                      <TableCell className="tabular-nums">{result.token_usage ? `${formatTokens(result.token_usage.input_tokens)} / ${formatTokens(result.token_usage.output_tokens)}` : '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </PageTransition>
  );
}
