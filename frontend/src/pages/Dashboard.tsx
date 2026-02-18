import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getDashboard } from '@/api/dashboard';
import type { EvalRun } from '@/types/run';
import { PageHeader } from '@/components/PageHeader';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/StatusBadge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { formatDate, formatPercent } from '@/lib/utils';
import { Plus, Play } from 'lucide-react';

export function Dashboard() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboard()
      .then((data) => setRuns(data.recent_runs))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton className="h-60 w-full" />;

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Overview of recent evaluation runs"
        action={
          <div className="flex gap-2">
            <Link to="/configs/new">
              <Button variant="outline" size="sm">
                <Plus className="mr-2 h-4 w-4" />
                New Config
              </Button>
            </Link>
            <Link to="/runs/new">
              <Button size="sm">
                <Play className="mr-2 h-4 w-4" />
                Start Run
              </Button>
            </Link>
          </div>
        }
      />

      {runs.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-foreground-secondary">No runs yet. Create a config and start your first evaluation.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {runs.map((run) => (
            <Link key={run.id} to={`/runs/${run.id}`} className="block">
              <Card className="p-4 hover:bg-background-hover transition-colors duration-150">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-foreground">{run.config_name ?? 'Unknown Config'}</p>
                    <p className="text-xs text-foreground-secondary mt-0.5">
                      Dataset: {run.dataset_name ?? 'Unknown'} · {formatDate(run.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    {run.summary && (
                      <span className="text-sm font-medium text-foreground">
                        {formatPercent(run.summary.accuracy)}
                      </span>
                    )}
                    <StatusBadge status={run.status} />
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
