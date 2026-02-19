import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getDashboard } from '@/api/dashboard';
import type { EvalRun } from '@/types/run';
import { PageHeader } from '@/components/PageHeader';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/StatusBadge';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { formatDate, formatPercent } from '@/lib/utils';
import { Plus, Play, ArrowRight } from 'lucide-react';

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

  if (loading) return <LoadingSkeleton rows={5} />;

  if (error) {
    return (
      <Alert variant="destructive" className="animate-fade-in">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  return (
    <PageTransition>
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
        <Card className="p-12 text-center animate-scale-in">
          <p className="text-foreground-secondary text-base">No runs yet. Create a config and start your first evaluation.</p>
          <div className="flex justify-center gap-3 mt-6">
            <Link to="/configs/new"><Button variant="outline" size="sm">Create Config</Button></Link>
            <Link to="/runs/new"><Button size="sm">Start Run</Button></Link>
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          {runs.map((run, idx) => (
            <Link key={run.id} to={`/runs/${run.id}`} className="block">
              <Card
                className="p-4 hover:bg-background-hover hover:border-border-hover hover:shadow-medium transition-all duration-200 ease-[var(--ease-smooth)] animate-fade-in-up"
                style={{ animationDelay: `${idx * 60}ms` }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground">{run.config_name ?? 'Unknown Config'}</p>
                    <p className="text-xs text-foreground-secondary mt-0.5">
                      Dataset: {run.dataset_name ?? 'Unknown'} · {formatDate(run.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    {run.summary && (
                      <span className="text-sm font-medium text-foreground tabular-nums">
                        {formatPercent(run.summary.accuracy)}
                      </span>
                    )}
                    <StatusBadge status={run.status} />
                    <ArrowRight className="h-4 w-4 text-foreground-disabled transition-transform duration-200 group-hover:translate-x-1" />
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </PageTransition>
  );
}
