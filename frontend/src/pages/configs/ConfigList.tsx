import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listConfigs, duplicateConfig } from '@/api/configs';
import type { EvalConfig } from '@/types/config';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Copy, Plus } from 'lucide-react';
import { formatDate } from '@/lib/utils';

export function ConfigList() {
  const [configs, setConfigs] = useState<EvalConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [duplicatingId, setDuplicatingId] = useState<string | null>(null);

  useEffect(() => {
    listConfigs()
      .then(setConfigs)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleDuplicate(e: React.MouseEvent, configId: string) {
    e.preventDefault();
    setDuplicatingId(configId);
    try {
      const copy = await duplicateConfig(configId);
      setConfigs((prev) => [copy, ...prev]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to duplicate config');
    } finally {
      setDuplicatingId(null);
    }
  }

  if (loading) return <LoadingSkeleton rows={4} />;
  if (error) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>;

  return (
    <PageTransition>
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
        <Card className="p-12 text-center animate-scale-in">
          <p className="text-foreground-secondary text-base">No configs yet.</p>
          <Link to="/configs/new"><Button className="mt-4" size="sm">Create your first config</Button></Link>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {configs.map((config, idx) => (
            <Link key={config.id} to={`/configs/${config.id}`}>
              <Card
                className="p-4 h-full hover:bg-background-hover hover:border-border-hover hover:shadow-medium transition-all duration-200 ease-[var(--ease-smooth)] animate-fade-in-up"
                style={{ animationDelay: `${idx * 60}ms` }}
              >
                <h3 className="text-sm font-medium text-foreground">{config.name}</h3>
                <p className="text-xs text-foreground-secondary mt-1 line-clamp-2">{config.system_prompt}</p>
                <div className="flex items-center gap-2 mt-3">
                  <Badge>{config.model}</Badge>
                  <Badge>{config.comparer_type}</Badge>
                </div>
                <div className="flex items-center justify-between mt-2">
                  <p className="text-xs text-foreground-disabled">{formatDate(config.created_at)}</p>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    disabled={duplicatingId === config.id}
                    onClick={(e) => handleDuplicate(e, config.id)}
                    title="Duplicate config"
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </PageTransition>
  );
}
