import { MessageSquare } from 'lucide-react';

import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface ConfigNotesFieldProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function ConfigNotesField({
  value,
  onChange,
  disabled,
}: ConfigNotesFieldProps) {
  const hasNote = value.trim().length > 0;

  return (
    <details className="group rounded-md border border-border-muted bg-background-secondary/40 px-3 py-2">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-xs text-foreground-secondary transition-colors duration-150 hover:text-foreground">
        <span className="flex items-center gap-2 font-medium">
          <MessageSquare className="h-3.5 w-3.5" />
          Notes
        </span>
        <span className="text-foreground-disabled">
          {hasNote ? 'Added' : 'Optional'}
        </span>
      </summary>
      <div className="mt-3 space-y-2">
        <Label className="text-xs text-foreground-secondary">Comment</Label>
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="What this config is for, what changed, or when to use it..."
          className="min-h-[72px] border-border-muted bg-background-input text-sm"
          disabled={disabled}
        />
        <p className="text-xs text-foreground-secondary">
          Optional context for teammates. This is not sent to the model.
        </p>
      </div>
    </details>
  );
}
