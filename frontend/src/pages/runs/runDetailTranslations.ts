import type { EvalResult } from '@/types/run';

export interface RunResultTranslationState {
  originalInputs: string[];
  originalInputRowIndexes: number[];
  resultIds: string[];
  targetLanguage: string;
  translatedInputs: string[];
}

interface RunSourceRow {
  [key: string]: string;
  input: string;
}

export function buildRunTranslationScope(results: EvalResult[]): string {
  return JSON.stringify(results.map((result) => result.id));
}

export function buildRunSourceRows(
  results: EvalResult[],
  translationState: RunResultTranslationState | null,
): RunSourceRow[] {
  return results.map((result, index) => ({
    input: translationState?.originalInputs[index] ?? result.input_data,
  }));
}

export function getRunInputForDisplay(
  result: EvalResult,
  rowIndex: number,
  translationState: RunResultTranslationState | null,
): string {
  if (!translationState) {
    return result.input_data;
  }
  if (translationState.originalInputRowIndexes.includes(rowIndex)) {
    return translationState.originalInputs[rowIndex] ?? result.input_data;
  }
  return translationState.translatedInputs[rowIndex] ?? result.input_data;
}
