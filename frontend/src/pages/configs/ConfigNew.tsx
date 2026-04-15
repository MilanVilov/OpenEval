import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { createConfig } from '@/api/configs';
import { fetchAllTags } from '@/api/configs';
import { generateSchema } from '@/api/generateSchema';
import { listVectorStores } from '@/api/vectorStores';
import { listContainers } from '@/api/containers';
import type { VectorStore } from '@/types/vectorStore';
import type { Container } from '@/types/container';
import { CustomGradersEditor } from '@/components/CustomGradersEditor';
import type { CustomGrader } from '@/types/config';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { PageTransition } from '@/components/PageTransition';
import { Spinner } from '@/components/Spinner';
import { TagInput } from '@/components/TagInput';
import { Lock } from 'lucide-react';

const MODEL_OPTIONS = [
  { group: 'Frontier', models: [
    { value: 'gpt-5.4', label: 'GPT-5.4' },
    { value: 'gpt-5.4-mini', label: 'GPT-5.4 Mini' },
    { value: 'gpt-5.4-nano', label: 'GPT-5.4 Nano' },
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
  'gpt-5.4', 'gpt-5.4-mini', 'gpt-5.4-nano',
  'gpt-5.2', 'gpt-5.2-pro', 'gpt-5.1', 'gpt-5', 'gpt-5-mini', 'gpt-5-nano',
  'o3', 'o3-pro', 'o3-mini', 'o4-mini',
]);

// Models that support xhigh reasoning effort
const XHIGH_REASONING_MODELS = new Set([
  'o3', 'o3-pro',
  'gpt-5.4', 'gpt-5.4-mini', 'gpt-5.4-nano',
]);

export function ConfigNew() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagSuggestions, setTagSuggestions] = useState<string[]>([]);
  const [systemPrompt, setSystemPrompt] = useState('');
  const [model, setModel] = useState('gpt-4.1');
  const [temperature, setTemperature] = useState('0.7');
  const [comparerTypes, setComparerTypes] = useState<Set<string>>(new Set(['exact_match']));
  const [customGraders, setCustomGraders] = useState<CustomGrader[]>([]);
  const [graderModel, setGraderModel] = useState('');
  const [graderThreshold, setGraderThreshold] = useState('0.7');
  const [concurrency, setConcurrency] = useState('5');
  const [reasoningEffort, setReasoningEffort] = useState('medium');
  const [reasoningSummary, setReasoningSummary] = useState('auto');
  const [responseFormatType, setResponseFormatType] = useState('text');
  const [jsonSchemaName, setJsonSchemaName] = useState('');
  const [jsonSchemaBody, setJsonSchemaBody] = useState('');
  const [aiSchemaPrompt, setAiSchemaPrompt] = useState('');
  const [aiSchemaLoading, setAiSchemaLoading] = useState(false);
  const [aiSchemaError, setAiSchemaError] = useState<string | null>(null);
  const [fileSearchEnabled, setFileSearchEnabled] = useState(false);
  const [vectorStoreId, setVectorStoreId] = useState('');
  const [vectorStores, setVectorStores] = useState<VectorStore[]>([]);
  const [shellEnabled, setShellEnabled] = useState(false);
  const [containerId, setContainerId] = useState('');
  const [containers, setContainers] = useState<Container[]>([]);
  const [toolChoice, setToolChoice] = useState('auto');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isReadonly, setIsReadonly] = useState(false);

  const isReasoningModel = REASONING_MODELS.has(model);
  const supportsXhigh = XHIGH_REASONING_MODELS.has(model);

  useEffect(() => {
    listVectorStores()
      .then(setVectorStores)
      .catch(() => {/* ignore – selector will be empty */});
    listContainers()
      .then(setContainers)
      .catch(() => {/* ignore – selector will be empty */});
    fetchAllTags()
      .then(setTagSuggestions)
      .catch(() => {/* ignore */});
  }, []);

  function buildResponseFormat(): Record<string, unknown> | null {
    if (responseFormatType === 'text') return null;
    if (responseFormatType === 'json_object') return { type: 'json_object' };
    if (responseFormatType === 'json_schema') {
      const safeName = (jsonSchemaName || 'response').replace(/[^a-zA-Z0-9_-]/g, '_');
      try {
        const schema = JSON.parse(jsonSchemaBody);
        return { type: 'json_schema', name: safeName, schema, strict: true };
      } catch {
        return { type: 'json_schema', name: safeName, schema: {}, strict: true };
      }
    }
    return null;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
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
      const gradersPayload = customGraders
        .filter((g) => g.name.trim() && g.prompt.trim())
        .map((g) => ({
          ...g,
          model: graderModel || undefined,
          threshold: parseFloat(graderThreshold) || 0.7,
        }));
      const config = await createConfig({
        name,
        system_prompt: systemPrompt,
        model,
        temperature: parseFloat(temperature),
        comparer_type: Array.from(comparerTypes).join(','),
        comparer_config: {},
        custom_graders: gradersPayload,
        tags,
        tools,
        tool_options: toolOptions,
        concurrency: parseInt(concurrency, 10),
        reasoning_config: reasoningConfig,
        response_format: buildResponseFormat(),
        readonly: isReadonly,
      });
      navigate(`/configs/${config.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageTransition>
      <PageHeader title="New Config" description="Create a new evaluation configuration" />
      <form onSubmit={handleSubmit} className="space-y-5 max-w-[640px]">
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

        <div className="space-y-2">
          <Label>Name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} required placeholder="My eval config" />
        </div>

        <div className="space-y-2">
          <Label>Tags</Label>
          <TagInput value={tags} onChange={setTags} suggestions={tagSuggestions} />
          <p className="text-xs text-foreground-secondary">Press Enter or comma to add a tag</p>
        </div>

        <div className="space-y-2">
          <Label>System Prompt</Label>
          <Textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} required placeholder="You are a helpful assistant..." className="font-mono min-h-[120px]" />
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
              {supportsXhigh && <option value="xhigh">Extra High</option>}
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
            <div className="space-y-2 rounded-md border border-dashed border-border p-3 bg-muted/30">
              <Label>Generate with AI</Label>
              <div className="flex gap-2">
                <Input
                  value={aiSchemaPrompt}
                  onChange={(e) => setAiSchemaPrompt(e.target.value)}
                  placeholder="Describe the schema, e.g. 'A product with name, price, and tags'"
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  disabled={aiSchemaLoading || !aiSchemaPrompt.trim()}
                  onClick={async () => {
                    setAiSchemaLoading(true);
                    setAiSchemaError(null);
                    try {
                      const result = await generateSchema(aiSchemaPrompt);
                      setJsonSchemaName(result.schema_name);
                      setJsonSchemaBody(JSON.stringify(result.schema_body, null, 2));
                    } catch (err) {
                      setAiSchemaError(err instanceof Error ? err.message : 'Generation failed');
                    } finally {
                      setAiSchemaLoading(false);
                    }
                  }}
                >
                  {aiSchemaLoading ? 'Generating...' : 'Generate'}
                </Button>
              </div>
              {aiSchemaError && <p className="text-xs text-destructive">{aiSchemaError}</p>}
              <p className="text-xs text-foreground-secondary">Uses GPT-5.2 to create a JSON schema from your description</p>
            </div>
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
                { value: 'json_field_match', label: 'JSON Field Match' },
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

        <CustomGradersEditor
          graders={customGraders}
          onChange={setCustomGraders}
          graderModel={graderModel}
          onGraderModelChange={setGraderModel}
          graderThreshold={graderThreshold}
          onGraderThresholdChange={setGraderThreshold}
        />

        <div className="rounded-md border border-border p-4 space-y-2">
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input
              type="checkbox"
              checked={isReadonly}
              onChange={(e) => setIsReadonly(e.target.checked)}
              className="rounded border-border"
            />
            <Lock className="h-3.5 w-3.5" />
            Lock configuration (readonly)
          </label>
          {isReadonly && (
            <p className="text-xs text-foreground-secondary">This config will be locked after creation. You can unlock it later from the edit page.</p>
          )}
        </div>

        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="outline" onClick={() => navigate('/configs')}>Cancel</Button>
          <Button type="submit" disabled={submitting}>
            {submitting && <Spinner className="mr-2" />}
            {submitting ? 'Creating...' : 'Create Config'}
          </Button>
        </div>
      </form>
    </PageTransition>
  );
}
