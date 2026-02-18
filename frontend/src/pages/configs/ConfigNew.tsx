import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { createConfig } from '@/api/configs';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';

export function ConfigNew() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [model, setModel] = useState('gpt-4o');
  const [temperature, setTemperature] = useState('0.7');
  const [comparerType, setComparerType] = useState('exact_match');
  const [concurrency, setConcurrency] = useState('5');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const config = await createConfig({
        name,
        system_prompt: systemPrompt,
        model,
        temperature: parseFloat(temperature),
        comparer_type: comparerType,
        comparer_config: {},
        tools: [],
        tool_options: {},
        concurrency: parseInt(concurrency, 10),
      });
      navigate(`/configs/${config.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <PageHeader title="New Config" description="Create a new evaluation configuration" />
      <form onSubmit={handleSubmit} className="space-y-4 max-w-[600px]">
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

        <div className="space-y-2">
          <Label>Name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} required placeholder="My eval config" />
        </div>

        <div className="space-y-2">
          <Label>System Prompt</Label>
          <Textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} required placeholder="You are a helpful assistant..." className="font-mono min-h-[120px]" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Model</Label>
            <Select value={model} onChange={(e) => setModel(e.target.value)}>
              <option value="gpt-4o">GPT-4o</option>
              <option value="gpt-4o-mini">GPT-4o Mini</option>
              <option value="gpt-4.1">GPT-4.1</option>
              <option value="gpt-4.1-mini">GPT-4.1 Mini</option>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Temperature</Label>
            <Input type="number" step="0.1" min="0" max="2" value={temperature} onChange={(e) => setTemperature(e.target.value)} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Comparer</Label>
            <Select value={comparerType} onChange={(e) => setComparerType(e.target.value)}>
              <option value="exact_match">Exact Match</option>
              <option value="pattern_match">Pattern Match</option>
              <option value="semantic_similarity">Semantic Similarity</option>
              <option value="llm_judge">LLM Judge</option>
              <option value="json_schema_match">JSON Schema Match</option>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Concurrency</Label>
            <Input type="number" min="1" max="20" value={concurrency} onChange={(e) => setConcurrency(e.target.value)} />
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="outline" onClick={() => navigate('/configs')}>Cancel</Button>
          <Button type="submit" disabled={submitting}>{submitting ? 'Creating...' : 'Create Config'}</Button>
        </div>
      </form>
    </div>
  );
}
