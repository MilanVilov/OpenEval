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
import { PageTransition } from '@/components/PageTransition';
import { Spinner } from '@/components/Spinner';
import { CodeBlock } from '@/components/CodeBlock';
import { Send, Clock, Zap, FileSearch, Terminal as TerminalIcon, MessageSquare, Brain, ChevronRight, CheckCircle2, XCircle } from 'lucide-react';

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
    <PageTransition>
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
                <><Spinner className="mr-2" />Running...</>
              ) : (
                <><Send className="mr-2 h-4 w-4" />Send</>
              )}
            </Button>
          </form>

          {error && <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>}
        </div>

        {/* Right: Response */}
        <div className="space-y-4">
          {result && (
            <div className="animate-fade-in-up space-y-4">
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
                      className={`text-sm font-medium px-3 py-1.5 rounded transition-all duration-200 ${
                        rawTab === 'request'
                          ? 'bg-accent-muted text-foreground shadow-sm'
                          : 'text-foreground-secondary hover:text-foreground hover:bg-background-hover'
                      }`}
                    >
                      Raw Request
                    </button>
                    <button
                      type="button"
                      onClick={() => setRawTab('response')}
                      className={`text-sm font-medium px-3 py-1.5 rounded transition-all duration-200 ${
                        rawTab === 'response'
                          ? 'bg-accent-muted text-foreground shadow-sm'
                          : 'text-foreground-secondary hover:text-foreground hover:bg-background-hover'
                      }`}
                    >
                      Raw Response
                    </button>
                  </div>
                </CardHeader>
                <CardContent>
                  <CodeBlock
                    code={rawTab === 'request'
                      ? JSON.stringify(result.raw_request, null, 2)
                      : JSON.stringify(result.raw_response, null, 2)}
                    language="json"
                    maxHeight="400px"
                  />
                </CardContent>
              </Card>
            </div>
          )}

          {!result && !loading && (
            <div className="flex items-center justify-center h-40 text-foreground-secondary text-sm">
              Send a message to see the response
            </div>
          )}
        </div>
      </div>
    </PageTransition>
  );
}

function OutputItemCard({ item }: { item: Record<string, unknown> }) {
  const type = item.type as string;

  if (type === 'reasoning') {
    const summary = item.summary as Array<Record<string, unknown>> | undefined;
    const texts = summary?.filter((s) => s.type === 'summary_text').map((s) => s.text as string) || [];
    if (texts.length === 0) return null;
    return (
      <Card className="animate-fade-in-up border-border/60">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2 text-foreground-secondary">
            <Brain className="h-4 w-4" />reasoning
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            {texts.map((t, i) => (
              <p key={i} className="text-sm text-foreground-secondary" dangerouslySetInnerHTML={{
                __html: t.replace(/\*\*(.*?)\*\*/g, '<strong class="text-foreground">$1</strong>')
              }} />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (type === 'message') {
    const content = item.content as Array<Record<string, unknown>> | undefined;
    const texts = content?.filter((c) => c.type === 'output_text').map((c) => c.text as string) || [];
    return (
      <Card className="animate-fade-in-up">
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />Message
          </CardTitle>
        </CardHeader>
        <CardContent>
          <CodeBlock code={texts.join('\n') || '(empty)'} language="text" />
        </CardContent>
      </Card>
    );
  }

  if (type === 'file_search_call') {
    const results = item.results as Array<Record<string, unknown>> | undefined;
    return (
      <Card className="animate-fade-in-up">
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
    const action = item.action as Record<string, unknown> | undefined;
    const commands = (action?.commands as string[]) || [];
    const callId = item.call_id as string | undefined;
    const status = item.status as string | undefined;
    return (
      <Card className="animate-fade-in-up">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <TerminalIcon className="h-4 w-4" />Shell
            {status && (
              <Badge variant={status === 'completed' ? 'default' : 'info'} className="text-[10px] font-normal">
                {status}
              </Badge>
            )}
          </CardTitle>
          {callId && <p className="text-xs text-foreground-secondary font-mono">{callId}</p>}
        </CardHeader>
        <CardContent className="space-y-3">
          {commands.length > 0 && (
            <div>
              <p className="text-xs text-foreground-secondary uppercase tracking-wider mb-1.5">Commands</p>
              <div className="space-y-1.5">
                {commands.map((cmd, i) => (
                  <div key={i} className="flex items-start gap-2 font-mono text-xs bg-[#1c1c28] text-green-400 rounded px-3 py-2">
                    <ChevronRight className="h-3.5 w-3.5 mt-0.5 shrink-0 text-green-500" />
                    <span className="break-all">{cmd}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {commands.length === 0 && (
            <CodeBlock code={JSON.stringify(item, null, 2)} language="json" maxHeight="200px" />
          )}
        </CardContent>
      </Card>
    );
  }

  if (type === 'shell_call_output') {
    const outputs = (item.output as Array<Record<string, unknown>>) || [];
    const callId = item.call_id as string | undefined;
    return (
      <Card className="animate-fade-in-up">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <TerminalIcon className="h-4 w-4" />shell_call_output
          </CardTitle>
          {callId && <p className="text-xs text-foreground-secondary font-mono">{callId}</p>}
        </CardHeader>
        <CardContent className="space-y-3">
          {outputs.map((out, i) => {
            const stdout = out.stdout as string | undefined;
            const stderr = out.stderr as string | undefined;
            const outcome = out.outcome as Record<string, unknown> | undefined;
            const exitCode = outcome?.exit_code as number | undefined;
            return (
              <div key={i} className="space-y-2">
                {outputs.length > 1 && (
                  <p className="text-xs text-foreground-secondary font-medium">Command {i + 1}</p>
                )}
                {outcome && (
                  <div className="flex items-center gap-1.5 text-xs">
                    {exitCode === 0 ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                    ) : (
                      <XCircle className="h-3.5 w-3.5 text-red-500" />
                    )}
                    <span className="font-mono text-foreground-secondary">exit {String(exitCode)}</span>
                  </div>
                )}
                {stdout && stdout.trim() && (
                  <div>
                    <p className="text-xs text-foreground-secondary uppercase tracking-wider mb-1">stdout</p>
                    <CodeBlock code={stdout} language="text" maxHeight="200px" />
                  </div>
                )}
                {stderr && stderr.trim() && (
                  <div>
                    <p className="text-xs text-red-400 uppercase tracking-wider mb-1">stderr</p>
                    <CodeBlock code={stderr} language="text" maxHeight="200px" />
                  </div>
                )}
                {i < outputs.length - 1 && <hr className="border-border/50" />}
              </div>
            );
          })}
          {outputs.length === 0 && (
            <p className="text-xs text-foreground-secondary">No output</p>
          )}
        </CardContent>
      </Card>
    );
  }

  // Generic fallback for other types (code_interpreter, etc.)
  return (
    <Card className="animate-fade-in-up">
      <CardHeader>
        <CardTitle className="text-sm">{type}</CardTitle>
      </CardHeader>
      <CardContent>
        <CodeBlock
          code={JSON.stringify(item, null, 2)}
          language="json"
          maxHeight="200px"
        />
      </CardContent>
    </Card>
  );
}
