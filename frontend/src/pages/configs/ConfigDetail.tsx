import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getConfig, deleteConfig } from '@/api/configs';
import type { EvalConfig } from '@/types/config';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { formatDate } from '@/lib/utils';
import { Pencil, Trash2 } from 'lucide-react';

export function ConfigDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [config, setConfig] = useState<EvalConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getConfig(id)
      .then(setConfig)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleDelete() {
    if (!id || !confirm('Delete this config?')) return;
    await deleteConfig(id);
    navigate('/configs');
  }

  if (loading) return <Skeleton className="h-60 w-full" />;
  if (error) return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;
  if (!config) return <Alert variant="destructive"><AlertDescription>Config not found</AlertDescription></Alert>;

  return (
    <div>
      <PageHeader
        title={config.name}
        description={`Created ${formatDate(config.created_at)}`}
        action={
          <div className="flex gap-2">
            <Link to={`/configs/${id}/edit`}>
              <Button variant="outline" size="sm"><Pencil className="mr-2 h-4 w-4" />Edit</Button>
            </Link>
            <Button variant="destructive" size="sm" onClick={handleDelete}>
              <Trash2 className="mr-2 h-4 w-4" />Delete
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>Configuration</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div>
              <p className="text-xs text-foreground-secondary uppercase">Model</p>
              <Badge>{config.model}</Badge>
            </div>
            <div>
              <p className="text-xs text-foreground-secondary uppercase">Temperature</p>
              <p className="text-sm">{config.temperature}</p>
            </div>
            <div>
              <p className="text-xs text-foreground-secondary uppercase">Comparer</p>
              <Badge>{config.comparer_type}</Badge>
            </div>
            <div>
              <p className="text-xs text-foreground-secondary uppercase">Concurrency</p>
              <p className="text-sm">{config.concurrency}</p>
            </div>
            {config.reasoning_config && (
              <div>
                <p className="text-xs text-foreground-secondary uppercase">Reasoning Effort</p>
                <Badge>{config.reasoning_config.effort}</Badge>
              </div>
            )}
            {config.response_format && (
              <div>
                <p className="text-xs text-foreground-secondary uppercase">Response Format</p>
                <Badge>{(config.response_format as Record<string, unknown>).type as string}</Badge>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>System Prompt</CardTitle></CardHeader>
          <CardContent>
            <pre className="text-sm font-mono bg-background-input p-3 rounded whitespace-pre-wrap">{config.system_prompt}</pre>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
