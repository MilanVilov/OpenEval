import type { CustomGrader, GraderType, StringCheckOperation } from '@/types/config';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { PythonCodeEditor } from '@/components/PythonCodeEditor';
import { Plus, Trash2 } from 'lucide-react';

const GRADER_MODEL_OPTIONS = [
  { group: '', models: [
    { value: '', label: 'Same as config model (default)' },
  ]},
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

const GRADER_TYPE_OPTIONS: { value: GraderType; label: string }[] = [
  { value: 'prompt', label: 'Prompt Grader' },
  { value: 'string_check', label: 'String Check' },
  { value: 'python', label: 'Python' },
];

const STRING_CHECK_OPERATIONS: { value: StringCheckOperation; label: string }[] = [
  { value: 'equals', label: 'Equals' },
  { value: 'not_equals', label: 'Does not equal' },
  { value: 'contains', label: 'Contains' },
  { value: 'contains_ignore_case', label: 'Contains (ignore case)' },
];

interface CustomGradersEditorProps {
  graders: CustomGrader[];
  onChange: (graders: CustomGrader[]) => void;
  disabled?: boolean;
}

export function CustomGradersEditor({
  graders,
  onChange,
  disabled,
}: CustomGradersEditorProps) {
  function addGrader() {
    onChange([
      ...graders,
      {
        name: '',
        type: 'prompt',
        prompt: '',
        threshold: 0.7,
      },
    ]);
  }

  function removeGrader(index: number) {
    onChange(graders.filter((_, i) => i !== index));
  }

  function updateGrader(index: number, field: keyof CustomGrader, value: string) {
    const parsed = field === 'threshold' ? (parseFloat(value) || 0.7) : field === 'weight' ? (parseFloat(value) || 0) : value;
    const updated = graders.map((g, i) => {
      if (i !== index) return g;
      const next = { ...g, [field]: parsed };
      // When switching type, initialize defaults for the new type
      if (field === 'type') {
        if (value === 'string_check' && !g.operation) {
          next.operation = 'equals';
        }
      }
      return next;
    });
    onChange(updated);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label>Custom Graders</Label>
        <Button type="button" variant="outline" size="sm" onClick={addGrader} disabled={disabled}>
          <Plus className="mr-1 h-3.5 w-3.5" />
          Add Grader
        </Button>
      </div>
      <p className="text-xs text-foreground-secondary">
        Add custom evaluation graders: LLM prompt-based, deterministic string checks, or Python code.
      </p>

      {graders.map((grader, index) => {
        const graderType = (grader.type ?? 'prompt') as GraderType;
        return (
          <div
            key={index}
            className="rounded-md border border-border p-3 space-y-2"
          >
            <div className="flex items-center justify-between gap-2">
              <Select
                value={graderType}
                onChange={(e) => updateGrader(index, 'type', e.target.value)}
                disabled={disabled}
                className="w-44"
              >
                {GRADER_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </Select>
              <Input
                value={grader.name}
                onChange={(e) => updateGrader(index, 'name', e.target.value)}
                placeholder="Grader name"
                className="flex-1"
                disabled={disabled}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeGrader(index)}
                className="text-destructive hover:text-destructive shrink-0"
                disabled={disabled}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>

            {/* Prompt grader fields */}
            {graderType === 'prompt' && (
              <>
                <Textarea
                  value={grader.prompt ?? ''}
                  onChange={(e) => updateGrader(index, 'prompt', e.target.value)}
                  placeholder={'Evaluate whether the actual output matches the expected output.\n\nUse {expected} and {actual} as placeholders:\n\nExpected: {expected}\nActual: {actual}\n\nScore 1.0 if correct, 0.0 if wrong.'}
                  className="font-mono min-h-[100px] text-sm"
                  disabled={disabled}
                />
                <p className="text-xs text-foreground-secondary">
                  Use <code className="font-mono bg-muted px-1 rounded">{'{expected}'}</code> and <code className="font-mono bg-muted px-1 rounded">{'{actual}'}</code> placeholders in your prompt. The LLM must return a JSON score.
                </p>
              </>
            )}

            {/* String check grader fields */}
            {graderType === 'string_check' && (
              <>
                <div className="space-y-1">
                  <Input
                    value={grader.input_value ?? ''}
                    onChange={(e) => updateGrader(index, 'input_value', e.target.value)}
                    placeholder="e.g. {{ sample.output_text }}"
                    className="font-mono text-sm"
                    disabled={disabled}
                  />
                  <p className="text-xs text-foreground-secondary">
                    Left side — use <code className="font-mono bg-muted px-1 rounded">{'{{ item.field }}'}</code> for CSV columns, <code className="font-mono bg-muted px-1 rounded">{'{{ sample.output_text }}'}</code> for LLM output
                  </p>
                </div>
                <Select
                  value={grader.operation ?? 'equals'}
                  onChange={(e) => updateGrader(index, 'operation', e.target.value)}
                  disabled={disabled}
                >
                  {STRING_CHECK_OPERATIONS.map((op) => (
                    <option key={op.value} value={op.value}>{op.label}</option>
                  ))}
                </Select>
                <div className="space-y-1">
                  <Input
                    value={grader.reference_value ?? ''}
                    onChange={(e) => updateGrader(index, 'reference_value', e.target.value)}
                    placeholder="e.g. {{ item.expected_output }}"
                    className="font-mono text-sm"
                    disabled={disabled}
                  />
                  <p className="text-xs text-foreground-secondary">
                    Right side — use <code className="font-mono bg-muted px-1 rounded">{'{{ item.field }}'}</code> for CSV columns
                  </p>
                </div>
              </>
            )}

            {/* Python grader fields */}
            {graderType === 'python' && (
              <>
                <PythonCodeEditor
                  value={grader.source_code ?? ''}
                  onChange={(val) => updateGrader(index, 'source_code', val)}
                  placeholder={'import re\n\ndef grade(sample, item) -> float:\n    output_text = sample[\'output_text\']\n    reference = item[\'expected_output\']\n    if re.search(re.escape(reference), output_text):\n        return 1.0\n    else:\n        return 0.0'}
                  disabled={disabled}
                />
                <p className="text-xs text-foreground-secondary">
                  Define a <code className="font-mono bg-muted px-1 rounded">grade(sample, item) → float</code> function.{' '}
                  <code className="font-mono bg-muted px-1 rounded">sample</code> has <code className="font-mono bg-muted px-1 rounded">output_text</code>;{' '}
                  <code className="font-mono bg-muted px-1 rounded">item</code> is the full CSV row.
                  Available modules: <code className="font-mono bg-muted px-1 rounded">re</code>, <code className="font-mono bg-muted px-1 rounded">json</code>, <code className="font-mono bg-muted px-1 rounded">math</code>.
                </p>
              </>
            )}

            {/* Per-grader model (prompt only) & threshold */}
            <div className={`grid ${graderType === 'prompt' ? 'grid-cols-3' : 'grid-cols-2'} gap-3 pt-1 border-t border-border`}>
              {graderType === 'prompt' && (
                <div className="space-y-1">
                  <Label className="text-xs">Model</Label>
                  <Select
                    value={grader.model ?? ''}
                    onChange={(e) => updateGrader(index, 'model', e.target.value)}
                    disabled={disabled}
                  >
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
                  <p className="text-xs text-foreground-secondary">Leave default to use config model</p>
                </div>
              )}
              <div className="space-y-1">
                <Label className="text-xs">Pass Threshold</Label>
                <Input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={String(grader.threshold ?? 0.7)}
                  onChange={(e) => updateGrader(index, 'threshold', e.target.value)}
                  disabled={disabled}
                />
                <p className="text-xs text-foreground-secondary">Minimum score (0–1) to pass</p>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Weight</Label>
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={String(grader.weight ?? 1)}
                  onChange={(e) => updateGrader(index, 'weight', e.target.value)}
                  disabled={disabled}
                />
                <p className="text-xs text-foreground-secondary">0 = informational only</p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
