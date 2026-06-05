import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/Spinner';
import type { RowTranslationProgress } from '@/lib/translateRowsSequentially';
import { Languages, RotateCcw } from 'lucide-react';

interface InputTranslationActionsProps {
  currentTranslationLanguage: string | null;
  translatedFields: string[];
  loading: boolean;
  progress: RowTranslationProgress | null;
  targetLanguage: string;
  onTargetLanguageChange: (value: string) => void;
  onTranslate: () => void;
  onReset: () => void;
}

export function InputTranslationActions({
  currentTranslationLanguage,
  translatedFields,
  loading,
  progress,
  targetLanguage,
  onTargetLanguageChange,
  onTranslate,
  onReset,
}: InputTranslationActionsProps) {
  const progressValue = progress
    ? Math.round((progress.completed / Math.max(progress.total, 1)) * 100)
    : 0;

  function renderTranslatedFields() {
    return translatedFields.map((field, index) => (
      <span key={field}>
        {index > 0 ? (index === translatedFields.length - 1 ? ' and ' : ', ') : null}
        <code>{field}</code>
      </span>
    ));
  }

  return (
    <div className="space-y-3 rounded-md border border-border bg-background-secondary/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">Translate Page Text</p>
          <p className="mt-1 text-xs text-foreground-secondary">
            Uses GPT-5.4 nano and only changes {renderTranslatedFields()} values for this page, one row at a time.
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

      {progress ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-foreground-secondary">
            <span>
              {loading && progress.activeRowIndex !== null
                ? `Translating row ${progress.activeRowIndex + 1} of ${progress.total}`
                : `Translated ${progress.completed} of ${progress.total} rows`}
            </span>
            <span>{progress.completed}/{progress.total}</span>
          </div>
          <Progress value={progressValue} />
        </div>
      ) : null}
    </div>
  );
}
