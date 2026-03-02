import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listRuns } from '@/api/runs';
import type { EvalRun } from '@/types/run';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { StatusBadge } from '@/components/StatusBadge';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card } from '@/components/ui/card';
import { Plus } from 'lucide-react';
import { formatDate, formatPercent, formatLatency, formatTokens } from '@/lib/utils';

export function RunList() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listRuns()
      .then(setRuns)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSkeleton rows={5} />;
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

      {runs.length === 0 ? (
        <Card className="p-12 text-center animate-scale-in">
          <p className="text-foreground-secondary text-base">No runs yet.</p>
          <Link to="/runs/new"><Button className="mt-4" size="sm">Start your first run</Button></Link>
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
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </PageTransition>
  );
}
