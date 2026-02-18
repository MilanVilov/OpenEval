import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listRuns } from '@/api/runs';
import type { EvalRun } from '@/types/run';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { StatusBadge } from '@/components/StatusBadge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card } from '@/components/ui/card';
import { Plus } from 'lucide-react';
import { formatDate, formatPercent } from '@/lib/utils';

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

  if (loading) return <Skeleton className="h-40 w-full" />;
  if (error) return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;

  return (
    <div>
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
        <Card className="p-8 text-center">
          <p className="text-foreground-secondary">No runs yet.</p>
          <Link to="/runs/new"><Button className="mt-4" size="sm">Start your first run</Button></Link>
        </Card>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Config</TableHead>
              <TableHead>Dataset</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Accuracy</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={run.id}>
                <TableCell>
                  <Link to={`/runs/${run.id}`} className="text-accent-blue hover:underline">
                    {run.config_name ?? 'Unknown'}
                  </Link>
                </TableCell>
                <TableCell>{run.dataset_name ?? 'Unknown'}</TableCell>
                <TableCell><StatusBadge status={run.status} /></TableCell>
                <TableCell>{run.summary ? formatPercent(run.summary.accuracy) : '—'}</TableCell>
                <TableCell>{formatDate(run.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
