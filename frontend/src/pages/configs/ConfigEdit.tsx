import { useState, useEffect, type FormEvent } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getConfig, updateConfig } from '@/api/configs';
import { listVectorStores } from '@/api/vectorStores';
import { listContainers } from '@/api/containers';
import type { VectorStore } from '@/types/vectorStore';
import type { Container } from '@/types/container';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';

const MODEL_OPTIONS = [
  { group: 'Frontier', models: [
    { value: 'gpt-5.2', label: 'GPT-5.2' },
    { value: 'gpt-5.2-pro', label: 'GPT-5.2 Pro' },
    { value: 'gpt-5.1', label: 'GPT-5.1' },
    { value: 'gpt-5', label: 'GPT-5' },
    { value: 'gpt-5-mini', label: 'GPT-5 Mini' },
    { value: 'gpt-5-nano', label: 'GPT-5 Nano' },
  ]},
  { group: 'Non-reasoning', models: [
    { value: 'gpt-4.1', label: 'GPT-4.1' },
    { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini' },
    { value: 'gpt-4.1-nano', label: 'GPT-4.1 Nano' },
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  ]},
  { group: 'Reasoning (o-series)', models: [
    { value: 'o3', label: 'o3' },
    { value: 'o3-pro', label: 'o3 Pro' },
    { value: 'o3-mini', label: 'o3 Mini' },
    { value: 'o4-mini', label: 'o4 Mini' },
  ]},
] as const;

const REASONING_MODELS = new Set([
  'gpt-5.2', 'gpt-5.2-pro', 'gpt-5.1', 'gpt-5', 'gpt-5-mini', 'gpt-5-nano',
  'o3', 'o3-pro', 'o3-mini', 'o4-mini',
]);

export function ConfigEdit() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [model, setModel] = useState('gpt-4.1');
  const [temperature, setTemperature] = useState('0.7');
  const [comparerTypes, setComparerTypes] = useState<Set<string>>(new Set(['exact_match']));
  const [concurrency, setConcurrency] = useState('5');
  const [reasoningEffort, setReasoningEffort] = useState('medium');
  const [reasoningSummary, setReasoningSummary] = useState('auto');
  const [responseFormatType, setResponseFormatType] = useState('text');
  const [jsonSchemaName, setJsonSchemaName] = useState('');
  const [jsonSchemaBody, setJsonSchemaBody] = useState('');
  const [fileSearchEnabled, setFileSearchEnabled] = useState(false);
  const [vectorStoreId, setVectorStoreId] = useState('');
  const [vectorStores, setVectorStores] = useState<VectorStore[]>([]);
  const [shellEnabled, setShellEnabled] = useState(false);
  const [containerId, setContainerId] = useState('');
  const [containers, setContainers] = useState<Container[]>([]);
  const [toolChoice, setToolChoice] = useState('auto');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isReasoningModel = REASONING_MODELS.has(model);

  useEffect(() => {
    listVectorStores()
      .then(setVectorStores)
      .catch(() => {/* ignore */});
    listContainers()
      .then(setContainers)
      .catch(() => {/* ignore */});
  }, []);

  useEffect(() => {
    if (!id) return;
    getConfig(id)
      .then((config) => {
        setName(config.name);
        setSystemPrompt(config.system_prompt);
        setModel(config.model);
        setTemperature(String(config.temperature));
        setComparerTypes(new Set(config.comparer_type.split(',').map((s: string) => s.trim())));
        setConcurrency(String(config.concurrency));
        if (config.reasoning_config?.effort) {
          setReasoningEffort(config.reasoning_config.effort);
        }
        if (config.reasoning_config) {
          const summary = (config.reasoning_config as Record<string, string>).summary;
          setReasoningSummary(summary ?? 'null');
        }
        if (config.response_format) {
          const fmt = config.response_format as Record<string, unknown>;
          const fmtType = (fmt.type as string) || 'text';
          setResponseFormatType(fmtType);
          if (fmtType === 'json_schema') {
            setJsonSchemaName((fmt.name as string) || '');
            setJsonSchemaBody(fmt.schema ? JSON.stringify(fmt.schema, null, 2) : '');
          }
        }
        // Load tools state
        if (config.tools && config.tools.includes('file_search')) {
          setFileSearchEnabled(true);
          setVectorStoreId((config.tool_options as Record<string, string>)?.vector_store_id || '');
        }
        if (config.tools && config.tools.includes('shell')) {
          setShellEnabled(true);
          setContainerId((config.tool_options as Record<string, string>)?.container_id || '');
        }
        if ((config.tool_options as Record<string, string>)?.tool_choice) {
          setToolChoice((config.tool_options as Record<string, string>).tool_choice);
        }
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  function buildResponseFormat(): Record<string, unknown> | null {
    if (responseFormatType === 'text') return null;
    if (responseFormatType === 'json_object') return { type: 'json_object' };
    if (responseFormatType === 'json_schema') {
      try {
        const schema = JSON.parse(jsonSchemaBody);
        return { type: 'json_schema', name: jsonSchemaName || 'response', schema, strict: true };
      } catch {
        return { type: 'json_schema', name: jsonSchemaName || 'response', schema: {}, strict: true };
      }
    }
    return null;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!id) return;
    setSubmitting(true);
    setError(null);
    try {
      const tools: string[] = [];
      const toolOptions: Record<string, unknown> = {};
      if (fileSearchEnabled) {
        tools.push('file_search');
        if (vectorStoreId) {
          toolOptions.vector_store_id = vectorStoreId;
        }
      }
      if (shellEnabled) {
        tools.push('shell');
        if (containerId) {
          toolOptions.container_id = containerId;
        }
      }
      if (tools.length > 0 && toolChoice !== 'auto') {
        toolOptions.tool_choice = toolChoice;
      }
      const reasoningConfig = isReasoningModel
        ? { effort: reasoningEffort, ...(reasoningSummary !== 'null' ? { summary: reasoningSummary } : {}) }
        : null;
      await updateConfig(id, {
        name,
        system_prompt: systemPrompt,
        model,
        temperature: parseFloat(temperature),
        comparer_type: Array.from(comparerTypes).join(','),
        tools,
        tool_options: toolOptions,
        concurrency: parseInt(concurrency, 10),
        reasoning_config: reasoningConfig,
        response_format: buildResponseFormat(),
      });
      navigate(`/configs/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <Skeleton className="h-40 w-full" />;

  return (
    <div>
      <PageHeader title="Edit Config" />
      <form onSubmit={handleSubmit} className="space-y-4 max-w-[600px]">
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

        <div className="space-y-2">
          <Label>Name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} required />
        </div>

        <div className="space-y-2">
          <Label>System Prompt</Label>
          <Textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} required className="font-mono min-h-[120px]" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Model</Label>
            <Select value={model} onChange={(e) => setModel(e.target.value)}>
              {MODEL_OPTIONS.map((group) => (
                <optgroup key={group.group} label={group.group}>
                  {group.models.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </optgroup>
              ))}
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Temperature</Label>
            <Input type="number" step="0.1" min="0" max="2" value={temperature} onChange={(e) => setTemperature(e.target.value)} />
          </div>
        </div>

        {isReasoningModel && (
          <>
          <div className="space-y-2">
            <Label>Reasoning Effort</Label>
            <Select value={reasoningEffort} onChange={(e) => setReasoningEffort(e.target.value)}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </Select>
            <p className="text-xs text-foreground-secondary">Controls how much reasoning compute the model uses</p>
          </div>
          <div className="space-y-2">
            <Label>Reasoning Summary</Label>
            <Select value={reasoningSummary} onChange={(e) => setReasoningSummary(e.target.value)}>
              <option value="auto">Auto</option>
              <option value="concise">Concise</option>
              <option value="detailed">Detailed</option>
              <option value="null">None (disabled)</option>
            </Select>
            <p className="text-xs text-foreground-secondary">Controls whether and how the model summarizes its reasoning</p>
          </div>
          </>
        )}

        <div className="space-y-2">
          <Label>Response Format</Label>
          <Select value={responseFormatType} onChange={(e) => setResponseFormatType(e.target.value)}>
            <option value="text">Plain Text</option>
            <option value="json_object">JSON Object</option>
            <option value="json_schema">JSON Schema (Structured Output)</option>
          </Select>
        </div>

        {responseFormatType === 'json_schema' && (
          <div className="space-y-3 rounded-md border border-border p-4">
            <div className="space-y-2">
              <Label>Schema Name</Label>
              <Input value={jsonSchemaName} onChange={(e) => setJsonSchemaName(e.target.value)} placeholder="response" />
            </div>
            <div className="space-y-2">
              <Label>JSON Schema</Label>
              <Textarea
                value={jsonSchemaBody}
                onChange={(e) => setJsonSchemaBody(e.target.value)}
                placeholder={'{\n  "type": "object",\n  "properties": {\n    "answer": { "type": "string" }\n  },\n  "required": ["answer"],\n  "additionalProperties": false\n}'}
                className="font-mono min-h-[160px]"
              />
              <p className="text-xs text-foreground-secondary">Define the JSON Schema for structured output. Must have "additionalProperties": false for strict mode.</p>
            </div>
          </div>
        )}

        <div className="space-y-2">
          <Label>Tools</Label>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={fileSearchEnabled}
              onChange={(e) => setFileSearchEnabled(e.target.checked)}
              className="rounded border-border"
            />
            File Search
          </label>
          <p className="text-xs text-foreground-secondary">Enable the model to search uploaded files in a vector store for relevant information</p>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={shellEnabled}
              onChange={(e) => setShellEnabled(e.target.checked)}
              className="rounded border-border"
            />
            Shell
          </label>
          <p className="text-xs text-foreground-secondary">Enable the model to run shell commands in an OpenAI-hosted container</p>
        </div>

        {(fileSearchEnabled || shellEnabled) && (
          <div className="space-y-2">
            <Label>Tool Choice</Label>
            <Select value={toolChoice} onChange={(e) => setToolChoice(e.target.value)}>
              <option value="auto">Auto (model decides)</option>
              <option value="required">Required (must use a tool)</option>
              <option value="none">None (tools available but suppressed)</option>
            </Select>
            <p className="text-xs text-foreground-secondary">Controls whether the model must, may, or must not call tools</p>
          </div>
        )}

        {fileSearchEnabled && (
          <div className="space-y-2 rounded-md border border-border p-4">
            <Label>Vector Store</Label>
            <Select value={vectorStoreId} onChange={(e) => setVectorStoreId(e.target.value)}>
              <option value="">— Select a vector store —</option>
              {vectorStores.map((vs) => (
                <option key={vs.id} value={vs.openai_vector_store_id}>{vs.name} ({vs.file_count} files)</option>
              ))}
            </Select>
            <p className="text-xs text-foreground-secondary">
              Select the vector store to search. <a href="/vector-stores/new" className="text-accent-blue hover:underline">Create a new one</a> if needed.
            </p>
          </div>
        )}

        {shellEnabled && (
          <div className="space-y-2 rounded-md border border-border p-4">
            <Label>Container</Label>
            <Select value={containerId} onChange={(e) => setContainerId(e.target.value)}>
              <option value="">— Auto (ephemeral container) —</option>
              {containers.map((c) => (
                <option key={c.id} value={c.openai_container_id}>{c.name} ({c.file_count} files)</option>
              ))}
            </Select>
            <p className="text-xs text-foreground-secondary">
              Select a container with pre-uploaded files, or leave as Auto. <a href="/containers/new" className="text-accent-blue hover:underline">Create a new one</a> if needed.
            </p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Comparers</Label>
            <div className="space-y-1">
              {[
                { value: 'exact_match', label: 'Exact Match' },
                { value: 'pattern_match', label: 'Pattern Match' },
                { value: 'semantic_similarity', label: 'Semantic Similarity' },
                { value: 'llm_judge', label: 'LLM Judge' },
                { value: 'json_schema_match', label: 'JSON Schema Match' },
                { value: 'contact_reason', label: 'Contact Reason' },
              ].map((c) => (
                <label key={c.value} className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={comparerTypes.has(c.value)}
                    onChange={(e) => {
                      const next = new Set(comparerTypes);
                      if (e.target.checked) next.add(c.value); else next.delete(c.value);
                      setComparerTypes(next);
                    }}
                    className="rounded border-border"
                  />
                  {c.label}
                </label>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <Label>Concurrency</Label>
            <Input type="number" min="1" max="20" value={concurrency} onChange={(e) => setConcurrency(e.target.value)} />
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="outline" onClick={() => navigate(`/configs/${id}`)}>Cancel</Button>
          <Button type="submit" disabled={submitting}>{submitting ? 'Saving...' : 'Save Changes'}</Button>
        </div>
      </form>
    </div>
  );
}
