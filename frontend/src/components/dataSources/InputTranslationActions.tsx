import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/Spinner';
import { Languages, RotateCcw } from 'lucide-react';

interface InputTranslationActionsProps {
  currentTranslationLanguage: string | null;
  loading: boolean;
  targetLanguage: string;
  onTargetLanguageChange: (value: string) => void;
  onTranslate: () => void;
  onReset: () => void;
}

export function InputTranslationActions({
  currentTranslationLanguage,
  loading,
  targetLanguage,
  onTargetLanguageChange,
  onTranslate,
  onReset,
}: InputTranslationActionsProps) {
  return (
    <div className="space-y-3 rounded-md border border-border bg-background-secondary/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">Translate Input Column</p>
          <p className="mt-1 text-xs text-foreground-secondary">
            Uses GPT-5.4 Nano and only changes mapped <code>input</code> values for this page.
          </p>
        </div>
        {currentTranslationLanguage ? (
          <Badge variant="info">Translated to {currentTranslationLanguage}</Badge>
        ) : null}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          value={targetLanguage}
          onChange={(event) => onTargetLanguageChange(event.target.value)}
          placeholder="English"
        />
        <Button type="button" variant="outline" onClick={onTranslate} disabled={loading}>
          {loading ? <Spinner className="mr-2" /> : <Languages className="mr-2 h-4 w-4" />}
          {loading ? 'Translating...' : 'Translate'}
        </Button>
        {currentTranslationLanguage ? (
          <Button type="button" variant="ghost" onClick={onReset} disabled={loading}>
            <RotateCcw className="mr-2 h-4 w-4" />
            Reset Page
          </Button>
        ) : null}
      </div>
    </div>
  );
}
