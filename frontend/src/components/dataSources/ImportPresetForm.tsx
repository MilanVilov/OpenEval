import { useState, type FormEvent } from 'react';
import type { ImportPreset, ImportPresetPayload } from '@/types/dataSource';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Spinner } from '@/components/Spinner';

interface ImportPresetFormProps {
  initial?: ImportPreset | null;
  error?: string | null;
  submitting: boolean;
  submitLabel: string;
  onSubmit: (payload: ImportPresetPayload) => Promise<void> | void;
}

export function ImportPresetForm({
  initial,
  error,
  submitting,
  submitLabel,
  onSubmit,
}: ImportPresetFormProps) {
  const [name, setName] = useState(() => initial?.name ?? '');
  const [recordsPath, setRecordsPath] = useState(() => initial?.records_path ?? '$.items');
  const [fieldMappingText, setFieldMappingText] = useState(() =>
    initial
      ? JSON.stringify(initial.field_mapping, null, 2)
      : '{\n  "input": "question",\n  "expected_output": "answer"\n}',
  );
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      const parsed = JSON.parse(fieldMappingText) as unknown;
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
        throw new Error('Field mapping must be a JSON object');
      }
      const fieldMapping = Object.fromEntries(
        Object.entries(parsed as Record<string, unknown>).map(([key, value]) => [key, String(value)]),
      );
      await onSubmit({
        name: name.trim(),
        records_path: recordsPath.trim(),
        field_mapping: fieldMapping,
      });
    } catch (submitError) {
      setFormError(submitError instanceof Error ? submitError.message : 'Invalid mapping JSON');
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {(error || formError) ? (
        <Alert variant="destructive">
          <AlertDescription>{error ?? formError}</AlertDescription>
        </Alert>
      ) : null}

      <div className="space-y-2">
        <Label>Preset Name</Label>
        <Input value={name} onChange={(event) => setName(event.target.value)} required placeholder="Ticket Mapping" />
      </div>

      <div className="space-y-2">
        <Label>Records Path</Label>
        <Input value={recordsPath} onChange={(event) => setRecordsPath(event.target.value)} required placeholder="$.items" />
      </div>

      <div className="space-y-2">
        <Label>Field Mapping JSON</Label>
        <Textarea
          value={fieldMappingText}
          onChange={(event) => setFieldMappingText(event.target.value)}
          rows={8}
          className="font-mono text-xs"
        />
        <p className="text-xs text-foreground-secondary">
          Required keys: <code>input</code> and <code>expected_output</code>.
        </p>
      </div>

      <Button type="submit" disabled={submitting}>
        {submitting ? <Spinner className="mr-2" /> : null}
        {submitting ? 'Saving...' : submitLabel}
      </Button>
    </form>
  );
}
