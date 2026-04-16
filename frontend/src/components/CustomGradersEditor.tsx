import type { Grader, GraderType, StringCheckOperation } from '@/types/config';
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
  { value: 'semantic_similarity', label: 'Semantic Similarity' },
  { value: 'json_schema', label: 'JSON Schema' },
  { value: 'json_field', label: 'JSON Field' },
];

const STRING_CHECK_OPERATIONS: { value: StringCheckOperation; label: string }[] = [
  { value: 'equals', label: 'Equals' },
  { value: 'not_equals', label: 'Does not equal' },
  { value: 'contains', label: 'Contains' },
  { value: 'contains_ignore_case', label: 'Contains (ignore case)' },
];

const GRADER_TYPE_DEFAULTS: Record<GraderType, Partial<Grader>> = {
  prompt: { prompt: '', threshold: 0.7 },
  string_check: { operation: 'equals', threshold: 0.7 },
  python: { source_code: '', threshold: 0.7 },
  semantic_similarity: { threshold: 0.8 },
  json_schema: { strict: false, threshold: 1.0 },
  json_field: { field_name: '', case_sensitive: false, strip_whitespace: true, threshold: 0.7 },
};

interface GradersEditorProps {
  graders: Grader[];
  onChange: (graders: Grader[]) => void;
  disabled?: boolean;
}

export function GradersEditor({
  graders,
  onChange,
  disabled,
}: GradersEditorProps) {
  function addGrader() {
    onChange([
      ...graders,
      {
        name: '',
        type: 'prompt',
        prompt: '',
        threshold: 0.7,
        weight: 1,
      },
    ]);
  }

  function removeGrader(index: number) {
    onChange(graders.filter((_, i) => i !== index));
  }

  function updateGrader(index: number, field: keyof Grader, value: string | boolean) {
    const parsed = field === 'threshold' || field === 'weight'
      ? (parseFloat(value as string) || 0)
      : field === 'strict' || field === 'case_sensitive' || field === 'strip_whitespace'
        ? value as boolean
        : value;
    const updated = graders.map((g, i) => {
      if (i !== index) return g;
      const next = { ...g, [field]: parsed };
      // When switching type, apply defaults for the new type
      if (field === 'type') {
        const defaults = GRADER_TYPE_DEFAULTS[value as GraderType] ?? {};
        Object.assign(next, defaults);
      }
      return next;
    });
    onChange(updated);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label>Graders</Label>
        <Button type="button" variant="outline" size="sm" onClick={addGrader} disabled={disabled}>
          <Plus className="mr-1 h-3.5 w-3.5" />
          Add Grader
        </Button>
      </div>
      <p className="text-xs text-foreground-secondary">
        Add evaluation graders: LLM prompt-based, string checks, Python code, semantic similarity, JSON schema, or JSON field matching.
      </p>

      {graders.map((grader, index) => {
        const graderType = (grader.type ?? 'prompt') as GraderType;
        const showModel = graderType === 'prompt' || graderType === 'semantic_similarity';
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

            {/* Semantic similarity grader — no extra fields besides model/threshold */}
            {graderType === 'semantic_similarity' && (
              <p className="text-xs text-foreground-secondary">
                Compares expected and actual outputs using cosine similarity of OpenAI embeddings. Select an embedding model below or use the config default.
              </p>
            )}

            {/* JSON schema grader fields */}
            {graderType === 'json_schema' && (
              <>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={grader.strict ?? false}
                    onChange={(e) => updateGrader(index, 'strict', e.target.checked)}
                    className="rounded border-border"
                    disabled={disabled}
                  />
                  Strict mode (actual must have exactly the same keys)
                </label>
                <p className="text-xs text-foreground-secondary">
                  Parses both expected and actual as JSON, then checks if all keys in expected exist in actual with matching values. Extra keys are allowed unless strict mode is enabled.
                </p>
              </>
            )}

            {/* JSON field grader fields */}
            {graderType === 'json_field' && (
              <>
                <div className="space-y-1">
                  <Label className="text-xs">Field Name</Label>
                  <Input
                    value={grader.field_name ?? ''}
                    onChange={(e) => updateGrader(index, 'field_name', e.target.value)}
                    placeholder="e.g. answer"
                    className="font-mono text-sm"
                    disabled={disabled}
                  />
                  <p className="text-xs text-foreground-secondary">
                    JSON field to extract from the LLM response (searched recursively)
                  </p>
                </div>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={grader.case_sensitive ?? false}
                      onChange={(e) => updateGrader(index, 'case_sensitive', e.target.checked)}
                      className="rounded border-border"
                      disabled={disabled}
                    />
                    Case sensitive
                  </label>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={grader.strip_whitespace ?? true}
                      onChange={(e) => updateGrader(index, 'strip_whitespace', e.target.checked)}
                      className="rounded border-border"
                      disabled={disabled}
                    />
                    Strip whitespace
                  </label>
                </div>
              </>
            )}

            {/* Per-grader model & threshold & weight */}
            <div className={`grid ${showModel ? 'grid-cols-3' : 'grid-cols-2'} gap-3 pt-1 border-t border-border`}>
              {showModel && (
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
                  <p className="text-xs text-foreground-secondary">
                    {graderType === 'semantic_similarity' ? 'Embedding model' : 'Leave default to use config model'}
                  </p>
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
