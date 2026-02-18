import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { compareRuns } from '@/api/runs';
import type { EvalRun, EvalResult } from '@/types/run';
import { PageHeader } from '@/components/PageHeader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { StatCard } from '@/components/StatCard';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { formatPercent } from '@/lib/utils';

interface CompareData {
  run_a: EvalRun | null;
  run_b: EvalRun | null;
  results_a: EvalResult[];
  results_b: EvalResult[];
}

export function RunCompare() {
  const [searchParams] = useSearchParams();
  const [data, setData] = useState<CompareData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const runA = searchParams.get('run_a');
    const runB = searchParams.get('run_b');
    if (!runA || !runB) {
      setError('Both run_a and run_b query parameters are required');
      setLoading(false);
      return;
    }
    compareRuns(runA, runB)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [searchParams]);

  if (loading) return <Skeleton className="h-60 w-full" />;
  if (error) return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;
  if (!data) return <Alert variant="destructive"><AlertDescription>Comparison data not available</AlertDescription></Alert>;

  const runA = data.run_a;
  const runB = data.run_b;

  return (
    <div>
      <PageHeader
        title="Compare Runs"
        description={`${runA?.config_name ?? 'Run A'} vs ${runB?.config_name ?? 'Run B'}`}
      />

      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card>
          <CardHeader><CardTitle>{runA?.config_name ?? 'Run A'}</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2">
              <StatCard label="Accuracy" value={runA?.summary ? formatPercent(runA.summary.accuracy) : '—'} />
              <StatCard label="Total" value={String(runA?.summary?.total ?? 0)} />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>{runB?.config_name ?? 'Run B'}</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2">
              <StatCard label="Accuracy" value={runB?.summary ? formatPercent(runB.summary.accuracy) : '—'} />
              <StatCard label="Total" value={String(runB?.summary?.total ?? 0)} />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Side-by-Side Results</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Input</TableHead>
                  <TableHead>Expected</TableHead>
                  <TableHead>Run A Output</TableHead>
                  <TableHead>A</TableHead>
                  <TableHead>Run B Output</TableHead>
                  <TableHead>B</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.results_a.map((ra, i) => {
                  const rb = data.results_b[i];
                  return (
                    <TableRow key={ra.id}>
                      <TableCell>{ra.row_index}</TableCell>
                      <TableCell className="max-w-[150px] truncate">{ra.input_data}</TableCell>
                      <TableCell className="max-w-[150px] truncate">{ra.expected_output}</TableCell>
                      <TableCell className="max-w-[150px] truncate">{ra.actual_output}</TableCell>
                      <TableCell>
                        <Badge variant={ra.passed ? 'success' : 'error'}>
                          {ra.passed ? '✓' : '✗'}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[150px] truncate">{rb?.actual_output ?? '—'}</TableCell>
                      <TableCell>
                        {rb ? (
                          <Badge variant={rb.passed ? 'success' : 'error'}>
                            {rb.passed ? '✓' : '✗'}
                          </Badge>
                        ) : '—'}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
