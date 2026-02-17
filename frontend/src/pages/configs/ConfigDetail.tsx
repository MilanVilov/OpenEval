import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getConfig, deleteConfig, duplicateConfig } from '@/api/configs';
import type { EvalConfig } from '@/types/config';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
import { CodeBlock } from '@/components/CodeBlock';
import { formatDate } from '@/lib/utils';
import { Copy, Pencil, Trash2 } from 'lucide-react';

export function ConfigDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [config, setConfig] = useState<EvalConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [duplicating, setDuplicating] = useState(false);

  useEffect(() => {
    if (!id) return;
    getConfig(id)
      .then(setConfig)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleDuplicate() {
    if (!id) return;
    setDuplicating(true);
    try {
      const copy = await duplicateConfig(id);
      navigate(`/configs/${copy.id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to duplicate config');
    } finally {
      setDuplicating(false);
    }
  }

  async function handleDelete() {
    if (!id || !confirm('Delete this config?')) return;
    await deleteConfig(id);
    navigate('/configs');
  }

  if (loading) return <LoadingSkeleton rows={5} />;
  if (error) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>;
  if (!config) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>Config not found</AlertDescription></Alert>;

  return (
    <PageTransition>
      <PageHeader
        title={config.name}
        description={`Created ${formatDate(config.created_at)}`}
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleDuplicate} disabled={duplicating}>
              <Copy className="mr-2 h-4 w-4" />{duplicating ? 'Duplicating…' : 'Duplicate'}
            </Button>
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
        <Card className="animate-fade-in-up" style={{ animationDelay: '60ms' }}>
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
              <p className="text-xs text-foreground-secondary uppercase">Comparers</p>
              <div className="flex flex-wrap gap-1">
                {config.comparer_type.split(',').map((c: string) => (
                  <Badge key={c.trim()}>{c.trim()}</Badge>
                ))}
              </div>
            </div>
            {config.custom_graders && config.custom_graders.length > 0 && (
              <div>
                <p className="text-xs text-foreground-secondary uppercase">Custom LLM Graders</p>
                <div className="space-y-2 mt-1">
                  {config.custom_graders.map((g, i) => (
                    <div key={i} className="rounded border border-border p-2 text-sm space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="default">{g.name || 'Unnamed'}</Badge>
                        <span className="text-xs text-foreground-secondary">
                          {g.model ? `model: ${g.model} · ` : ''}threshold: {g.threshold}
                        </span>
                      </div>
                      <p className="text-xs text-foreground-secondary font-mono line-clamp-2">{g.prompt}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div>
              <p className="text-xs text-foreground-secondary uppercase">Concurrency</p>
              <p className="text-sm">{config.concurrency}</p>
            </div>
            {config.reasoning_config && (
              <div>
                <p className="text-xs text-foreground-secondary uppercase">Reasoning</p>
                <div className="flex gap-1">
                  <Badge>effort: {config.reasoning_config.effort}</Badge>
                  {(config.reasoning_config as Record<string, string>).summary && (
                    <Badge>summary: {(config.reasoning_config as Record<string, string>).summary}</Badge>
                  )}
                </div>
              </div>
            )}
            {config.response_format && (
              <div>
                <p className="text-xs text-foreground-secondary uppercase">Response Format</p>
                <Badge>{(config.response_format as Record<string, unknown>).type as string}</Badge>
              </div>
            )}
            {config.tools && config.tools.length > 0 && (
              <div>
                <p className="text-xs text-foreground-secondary uppercase">Tools</p>
                <div className="flex flex-wrap gap-1">
                  {config.tools.map((t: string) => (
                    <Badge key={t}>{t}</Badge>
                  ))}
                </div>
                {config.tools.includes('file_search') && (config.tool_options as Record<string, string>)?.vector_store_id && (
                  <p className="text-xs text-foreground-secondary mt-1">
                    Vector Store: <span className="font-mono">{(config.tool_options as Record<string, string>).vector_store_id}</span>
                  </p>
                )}
                {config.tools.includes('shell') && (
                  <p className="text-xs text-foreground-secondary mt-1">
                    Container: <span className="font-mono">{(config.tool_options as Record<string, string>)?.container_id || 'Auto (ephemeral)'}</span>
                  </p>
                )}
                {(config.tool_options as Record<string, string>)?.tool_choice && (
                  <p className="text-xs text-foreground-secondary mt-1">
                    Tool Choice: <span className="font-mono">{(config.tool_options as Record<string, string>).tool_choice}</span>
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="animate-fade-in-up" style={{ animationDelay: '120ms' }}>
          <CardHeader><CardTitle>System Prompt</CardTitle></CardHeader>
          <CardContent>
            <CodeBlock code={config.system_prompt} language="text" expandable expandTitle="System Prompt" />
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
