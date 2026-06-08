import type { StringRecord } from './translateRowsSequentially';

export interface TranslatedPageState<TRow extends StringRecord> {
  originalRowIndexes: number[];
  originalRows: TRow[];
  targetLanguage: string;
  translatedRows: TRow[];
}

export function buildDisplayRow<TRow extends StringRecord>(
  fallbackRow: TRow,
  rowIndex: number,
  translationState: TranslatedPageState<TRow> | null,
): TRow {
  if (!translationState) {
    return fallbackRow;
  }
  if (translationState.originalRowIndexes.includes(rowIndex)) {
    return translationState.originalRows[rowIndex] ?? fallbackRow;
  }
  return translationState.translatedRows[rowIndex] ?? fallbackRow;
}

export function buildDisplayRows<TRow extends StringRecord>(
  fallbackRows: TRow[],
  translationState: TranslatedPageState<TRow> | null,
): TRow[] {
  return fallbackRows.map((row, index) => buildDisplayRow(row, index, translationState));
}

export function rowHasTranslatedChanges<TRow extends StringRecord>(
  translationState: TranslatedPageState<TRow> | null,
  rowIndex: number,
  translatedFields: string[],
): boolean {
  if (!translationState) {
    return false;
  }

  const originalRow = translationState.originalRows[rowIndex];
  const translatedRow = translationState.translatedRows[rowIndex];
  if (!originalRow || !translatedRow) {
    return false;
  }

  return translatedFields.some(
    (field) => (originalRow[field] ?? '') !== (translatedRow[field] ?? ''),
  );
}

export function toggleOriginalRowIndexes(
  originalRowIndexes: number[],
  rowIndex: number,
): number[] {
  if (originalRowIndexes.includes(rowIndex)) {
    return originalRowIndexes.filter((currentIndex) => currentIndex !== rowIndex);
  }
  return [...originalRowIndexes, rowIndex];
}
