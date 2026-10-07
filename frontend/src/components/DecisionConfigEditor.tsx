import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { decisionQuestionExample, parseDecisionConfig } from '@/lib/decisionConfig';

interface DecisionConfigEditorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function DecisionConfigEditor({ value, onChange, disabled = false }: DecisionConfigEditorProps) {
  let error: string | null = null;
  try {
    parseDecisionConfig(value);
  } catch (err) {
    error = err instanceof Error ? err.message : 'Invalid decision questions';
  }
  return (
    <section className="space-y-3 rounded-md border border-border p-4">
      <div className="space-y-1">
        <h2 className="text-sm font-medium">Decisions API questions</h2>
        <p className="text-xs text-foreground-secondary">
          Evaluate each dataset input with GPT-6 Luna. Add named questions as a JSON array.
          Shared instructions above are included in every question.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {(['predicate', 'choice', 'score'] as const).map((type) => (
          <Button key={type} type="button" variant="outline" size="sm" disabled={disabled}
            onClick={() => onChange(decisionQuestionExample(type))}>
            Load {type} example
          </Button>
        ))}
      </div>
      <p className="text-xs text-foreground-secondary">Loading an example replaces the questions below.</p>
      <div className="space-y-2">
        <Label htmlFor="decision-questions">Questions (JSON)</Label>
        <Textarea id="decision-questions" value={value} disabled={disabled} required
          onChange={(event) => onChange(event.target.value)}
          className="font-mono min-h-[240px]" aria-invalid={Boolean(error)} aria-describedby="decision-help" />
        {error && <p role="alert" className="text-xs text-destructive">{error}</p>}
      </div>
      <div id="decision-help" className="space-y-1 text-xs text-foreground-secondary">
        <p>Predicate returns a probability from 0 to 1.</p>
        <p>Choice returns a supplied string or boolean value. Descriptions are optional.</p>
        <p>Score returns a weighted level index, starting at 0. List levels in ascending order.</p>
        <p>Output is JSON with an answers array, including question names and probabilities.</p>
        <p>Prompt graders without a model selected use GPT-4.1 for Decisions configurations.</p>
        <a href="https://developers.openai.com/api/docs/guides/decisions" target="_blank" rel="noreferrer"
          className="text-accent-blue hover:underline">Decisions API documentation</a>
      </div>
    </section>
  );
}
