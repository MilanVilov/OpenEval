import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { compareRuns } from '@/api/runs';
import type { EvalRun, EvalResult } from '@/types/run';
import { PageHeader } from '@/components/PageHeader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { StatCard } from '@/components/StatCard';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
import { formatPercent } from '@/lib/utils';

interface CompareData {
  run_a: EvalRun | null;
  run_b: EvalRun | null;
  results_a: EvalResult[];
  results_b: EvalResult[];
}

export function RunCompare() {
  const [searchParams] = useSearchParams();
  const runAId = searchParams.get('run_a');
  const runBId = searchParams.get('run_b');
  const missingParamsError = !runAId || !runBId
    ? 'Both run_a and run_b query parameters are required'
    : null;
  const requestKey = runAId && runBId ? `${runAId}:${runBId}` : null;
  const [resolvedKey, setResolvedKey] = useState<string | null>(null);
  const [data, setData] = useState<CompareData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runAId || !runBId || !requestKey) {
      return;
    }
    let active = true;

    compareRuns(runAId, runBId)
      .then((result) => {
        if (!active) {
          return;
        }
        setData(result);
        setError(null);
        setResolvedKey(requestKey);
      })
      .catch((compareError: Error) => {
        if (!active) {
          return;
        }
        setData(null);
        setError(compareError.message);
        setResolvedKey(requestKey);
      });

    return () => {
      active = false;
    };
  }, [requestKey, runAId, runBId]);

  const loading = Boolean(requestKey) && resolvedKey !== requestKey;
  const displayError = missingParamsError ?? (resolvedKey === requestKey ? error : null);
  const displayData = resolvedKey === requestKey ? data : null;

  if (loading) return <LoadingSkeleton rows={5} />;
  if (displayError) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{displayError}</AlertDescription></Alert>;
  if (!displayData) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>Comparison data not available</AlertDescription></Alert>;

  const runA = displayData.run_a;
  const runB = displayData.run_b;

  return (
    <PageTransition>
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
                {displayData.results_a.map((ra, i) => {
                  const rb = displayData.results_b[i];
                  return (
                    <TableRow key={ra.id}>
                      <TableCell>{ra.row_index}</TableCell>
                      <TableCell className="min-w-[150px] max-w-[300px] whitespace-pre-wrap break-words">{ra.input_data}</TableCell>
                      <TableCell className="min-w-[150px] max-w-[300px] whitespace-pre-wrap break-words">{ra.expected_output}</TableCell>
                      <TableCell className="min-w-[150px] max-w-[300px] whitespace-pre-wrap break-words">{ra.actual_output}</TableCell>
                      <TableCell>
                        <Badge variant={ra.passed ? 'success' : 'error'}>
                          {ra.passed ? '✓' : '✗'}
                        </Badge>
                      </TableCell>
                      <TableCell className="min-w-[150px] max-w-[300px] whitespace-pre-wrap break-words">{rb?.actual_output ?? '—'}</TableCell>
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
    </PageTransition>
  );
}
