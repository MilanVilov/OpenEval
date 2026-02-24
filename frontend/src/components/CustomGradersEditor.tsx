import type { CustomGrader } from '@/types/config';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Plus, Trash2 } from 'lucide-react';

const GRADER_MODEL_OPTIONS = [
  { group: '', models: [
    { value: '', label: 'Same as config model (default)' },
  ]},
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

interface CustomGradersEditorProps {
  graders: CustomGrader[];
  onChange: (graders: CustomGrader[]) => void;
  graderModel: string;
  onGraderModelChange: (model: string) => void;
  graderThreshold: string;
  onGraderThresholdChange: (threshold: string) => void;
}

export function CustomGradersEditor({
  graders,
  onChange,
  graderModel,
  onGraderModelChange,
  graderThreshold,
  onGraderThresholdChange,
}: CustomGradersEditorProps) {
  function addGrader() {
    onChange([
      ...graders,
      {
        name: '',
        prompt: '',
        threshold: parseFloat(graderThreshold) || 0.7,
      },
    ]);
  }

  function removeGrader(index: number) {
    onChange(graders.filter((_, i) => i !== index));
  }

  function updateGrader(index: number, field: keyof CustomGrader, value: string) {
    const updated = graders.map((g, i) =>
      i === index ? { ...g, [field]: value } : g,
    );
    onChange(updated);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label>Custom LLM Graders</Label>
        <Button type="button" variant="outline" size="sm" onClick={addGrader}>
          <Plus className="mr-1 h-3.5 w-3.5" />
          Add Grader
        </Button>
      </div>
      <p className="text-xs text-foreground-secondary">
        Add custom LLM-based evaluation graders with your own prompt. By default graders use the config model.
      </p>

      {graders.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <Label className="text-xs">Grader Model</Label>
            <Select value={graderModel} onChange={(e) => onGraderModelChange(e.target.value)}>
              {GRADER_MODEL_OPTIONS.map((group) =>
                group.group ? (
                  <optgroup key={group.group} label={group.group}>
                    {group.models.map((m) => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </optgroup>
                ) : (
                  group.models.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))
                )
              )}
            </Select>
            <p className="text-xs text-foreground-secondary">Leave as default to use the config model</p>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Pass Threshold</Label>
            <Input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={graderThreshold}
              onChange={(e) => onGraderThresholdChange(e.target.value)}
            />
            <p className="text-xs text-foreground-secondary">Minimum score (0–1) to pass</p>
          </div>
        </div>
      )}

      {graders.map((grader, index) => (
        <div
          key={index}
          className="rounded-md border border-border p-3 space-y-2"
        >
          <div className="flex items-center justify-between gap-2">
            <Input
              value={grader.name}
              onChange={(e) => updateGrader(index, 'name', e.target.value)}
              placeholder="Grader name (e.g. Tone Check)"
              className="flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => removeGrader(index)}
              className="text-destructive hover:text-destructive shrink-0"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
          <Textarea
            value={grader.prompt}
            onChange={(e) => updateGrader(index, 'prompt', e.target.value)}
            placeholder={'Evaluate whether the actual output matches the expected output.\n\nUse {expected} and {actual} as placeholders:\n\nExpected: {expected}\nActual: {actual}\n\nScore 1.0 if correct, 0.0 if wrong.'}
            className="font-mono min-h-[100px] text-sm"
          />
          <p className="text-xs text-foreground-secondary">
            Use <code className="font-mono bg-muted px-1 rounded">{'{expected}'}</code> and <code className="font-mono bg-muted px-1 rounded">{'{actual}'}</code> placeholders in your prompt. The LLM must return a JSON score.
          </p>
        </div>
      ))}
    </div>
  );
}
