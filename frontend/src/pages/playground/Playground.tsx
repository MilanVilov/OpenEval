import { useState, useEffect, type FormEvent } from 'react';
import { listConfigs } from '@/api/configs';
import { runPlayground, type PlaygroundResponse } from '@/api/playground';
import type { EvalConfig } from '@/types/config';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Send, Loader2, Clock, Zap, FileSearch, Terminal as TerminalIcon, MessageSquare } from 'lucide-react';

export function Playground() {
  const [configs, setConfigs] = useState<EvalConfig[]>([]);
  const [configId, setConfigId] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PlaygroundResponse | null>(null);
  const [rawTab, setRawTab] = useState<'request' | 'response'>('response');

  useEffect(() => {
    listConfigs()
      .then((list) => {
        setConfigs(list);
        if (list.length > 0) setConfigId(list[0].id);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const selectedConfig = configs.find((c) => c.id === configId);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!configId || !message.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await runPlayground({ config_id: configId, message: message.trim() });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  const outputItems = (result?.raw_response?.output as Array<Record<string, unknown>>) || [];

  return (
    <div>
      <PageHeader title="Playground" description="Test a config with a single message and inspect the full OpenAI response" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Input */}
        <div className="space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>Config</Label>
              <Select value={configId} onChange={(e) => setConfigId(e.target.value)}>
                <option value="">— Select a config —</option>
                {configs.map((c) => (
                  <option key={c.id} value={c.id}>{c.name} ({c.model})</option>
                ))}
              </Select>
            </div>

            {selectedConfig && (
              <div className="flex flex-wrap gap-1 text-xs">
                <Badge>{selectedConfig.model}</Badge>
                {selectedConfig.tools.map((t) => (
                  <Badge key={t} variant="info">{t}</Badge>
                ))}
                {selectedConfig.reasoning_config && (
                  <Badge variant="info">reasoning: {selectedConfig.reasoning_config.effort}</Badge>
                )}
              </div>
            )}

            <div className="space-y-2">
              <Label>Message</Label>
              <Textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Type your test message here..."
                className="font-mono min-h-[160px]"
                required
              />
            </div>

            <Button type="submit" disabled={loading || !configId || !message.trim()}>
              {loading ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Running...</>
              ) : (
                <><Send className="mr-2 h-4 w-4" />Send</>
              )}
            </Button>
          </form>

          {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        </div>

        {/* Right: Response */}
        <div className="space-y-4">
          {result && (
            <>
              {/* Stats */}
              <div className="flex gap-3 flex-wrap">
                <Badge className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />{result.latency_ms}ms
                </Badge>
                <Badge className="flex items-center gap-1">
                  <Zap className="h-3 w-3" />{result.token_usage.input_tokens} in / {result.token_usage.output_tokens} out
                </Badge>
                <Badge>
                  {String(result.raw_response.model)}
                </Badge>
              </div>

              {/* Output Items */}
              {outputItems.map((item, idx) => (
                <OutputItemCard key={idx} item={item} />
              ))}

              {/* Raw JSON with tabs */}
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setRawTab('request')}
                      className={`text-sm font-medium px-2 py-1 rounded transition-colors ${
                        rawTab === 'request'
                          ? 'bg-accent-muted text-foreground'
                          : 'text-foreground-secondary hover:text-foreground'
                      }`}
                    >
                      Raw Request
                    </button>
                    <button
                      type="button"
                      onClick={() => setRawTab('response')}
                      className={`text-sm font-medium px-2 py-1 rounded transition-colors ${
                        rawTab === 'response'
                          ? 'bg-accent-muted text-foreground'
                          : 'text-foreground-secondary hover:text-foreground'
                      }`}
                    >
                      Raw Response
                    </button>
                  </div>
                </CardHeader>
                <CardContent>
                  <pre className="text-xs font-mono bg-background-input p-3 rounded overflow-auto max-h-[400px] whitespace-pre-wrap">
                    {rawTab === 'request'
                      ? JSON.stringify(result.raw_request, null, 2)
                      : JSON.stringify(result.raw_response, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            </>
          )}

          {!result && !loading && (
            <div className="flex items-center justify-center h-40 text-foreground-secondary text-sm">
              Send a message to see the response
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function OutputItemCard({ item }: { item: Record<string, unknown> }) {
  const type = item.type as string;

  if (type === 'message') {
    const content = item.content as Array<Record<string, unknown>> | undefined;
    const texts = content?.filter((c) => c.type === 'output_text').map((c) => c.text as string) || [];
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />Message
          </CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="text-sm font-mono bg-background-input p-3 rounded whitespace-pre-wrap">
            {texts.join('\n') || '(empty)'}
          </pre>
        </CardContent>
      </Card>
    );
  }

  if (type === 'file_search_call') {
    const results = item.results as Array<Record<string, unknown>> | undefined;
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <FileSearch className="h-4 w-4" />File Search
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {results && results.length > 0 ? (
            results.map((r, i) => (
              <div key={i} className="text-xs border border-border rounded p-2">
                <p className="font-semibold">{r.filename as string || r.file_id as string}</p>
                <p className="text-foreground-secondary mt-1 line-clamp-3">{r.text as string}</p>
                {r.score != null && <Badge className="mt-1">score: {String(r.score)}</Badge>}
              </div>
            ))
          ) : (
            <p className="text-xs text-foreground-secondary">No results returned</p>
          )}
        </CardContent>
      </Card>
    );
  }

  if (type === 'shell_call') {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <TerminalIcon className="h-4 w-4" />Shell
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {item.command != null && (
            <div>
              <p className="text-xs text-foreground-secondary uppercase mb-1">Command</p>
              <pre className="text-xs font-mono bg-background-input p-2 rounded whitespace-pre-wrap">
                {JSON.stringify(item.command, null, 2)}
              </pre>
            </div>
          )}
          {item.output != null && (
            <div>
              <p className="text-xs text-foreground-secondary uppercase mb-1">Output</p>
              <pre className="text-xs font-mono bg-background-input p-2 rounded whitespace-pre-wrap max-h-[200px] overflow-auto">
                {typeof item.output === 'string' ? item.output : JSON.stringify(item.output, null, 2)}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  // Generic fallback for other types (code_interpreter, etc.)
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{type}</CardTitle>
      </CardHeader>
      <CardContent>
        <pre className="text-xs font-mono bg-background-input p-3 rounded overflow-auto max-h-[200px] whitespace-pre-wrap">
          {JSON.stringify(item, null, 2)}
        </pre>
      </CardContent>
    </Card>
  );
}
