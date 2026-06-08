import type { EvalResult } from '@/types/run';
import type { TranslatedPageState } from '@/lib/translatedPageRows';

export interface RunTranslationRow {
  [key: string]: string;
  actual_output: string;
  expected_output: string;
  input: string;
}

export interface RunResultTranslationState extends TranslatedPageState<RunTranslationRow> {
  resultIds: string[];
}

function resultToTranslationRow(result: EvalResult): RunTranslationRow {
  return {
    actual_output: result.actual_output ?? '',
    expected_output: result.expected_output,
    input: result.input_data,
  };
}

export function buildRunTranslationScope(results: EvalResult[]): string {
  return JSON.stringify(results.map((result) => result.id));
}

export function buildRunSourceRows(
  results: EvalResult[],
  translationState: RunResultTranslationState | null,
): RunTranslationRow[] {
  return results.map((result, index) => ({
    ...(translationState?.originalRows[index] ?? resultToTranslationRow(result)),
  }));
}

export function getRunRowForDisplay(
  result: EvalResult,
  rowIndex: number,
  translationState: RunResultTranslationState | null,
): RunTranslationRow {
  if (!translationState) {
    return resultToTranslationRow(result);
  }
  if (translationState.originalRowIndexes.includes(rowIndex)) {
    return translationState.originalRows[rowIndex] ?? resultToTranslationRow(result);
  }
  return translationState.translatedRows[rowIndex] ?? resultToTranslationRow(result);
}
