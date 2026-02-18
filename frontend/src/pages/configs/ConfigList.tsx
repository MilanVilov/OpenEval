import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listConfigs } from '@/api/configs';
import type { EvalConfig } from '@/types/config';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Plus } from 'lucide-react';
import { formatDate } from '@/lib/utils';

export function ConfigList() {
  const [configs, setConfigs] = useState<EvalConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listConfigs()
      .then(setConfigs)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton className="h-40 w-full" />;
  if (error) return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;

  return (
    <div>
      <PageHeader
        title="Eval Configs"
        description="Manage your evaluation configurations"
        action={
          <Link to="/configs/new">
            <Button size="sm"><Plus className="mr-2 h-4 w-4" />New Config</Button>
          </Link>
        }
      />

      {configs.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-foreground-secondary">No configs yet.</p>
          <Link to="/configs/new"><Button className="mt-4" size="sm">Create your first config</Button></Link>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {configs.map((config) => (
            <Link key={config.id} to={`/configs/${config.id}`}>
              <Card className="p-4 hover:bg-background-hover transition-colors duration-150 h-full">
                <h3 className="text-sm font-medium text-foreground">{config.name}</h3>
                <p className="text-xs text-foreground-secondary mt-1 line-clamp-2">{config.system_prompt}</p>
                <div className="flex items-center gap-2 mt-3">
                  <Badge>{config.model}</Badge>
                  <Badge>{config.comparer_type}</Badge>
                </div>
                <p className="text-xs text-foreground-disabled mt-2">{formatDate(config.created_at)}</p>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
