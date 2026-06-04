export interface StringRecord {
  [key: string]: string;
}

export interface RowTranslationProgress {
  activeRowIndex: number | null;
  completed: number;
  total: number;
}

interface TranslateRowsSequentiallyArgs<TRow extends StringRecord> {
  rows: TRow[];
  targetLanguage: string;
  translateRow: (row: TRow, targetLanguage: string) => Promise<TRow>;
  onProgress?: (progress: RowTranslationProgress) => void;
  onRowTranslated?: (rowIndex: number, translatedRow: TRow) => void;
}

export async function translateRowsSequentially<TRow extends StringRecord>({
  rows,
  targetLanguage,
  translateRow,
  onProgress,
  onRowTranslated,
}: TranslateRowsSequentiallyArgs<TRow>): Promise<TRow[]> {
  const translatedRows = rows.map((row) => ({ ...row }));
  const total = rows.length;

  if (total === 0) {
    onProgress?.({
      activeRowIndex: null,
      completed: 0,
      total: 0,
    });
    return translatedRows;
  }

  onProgress?.({
    activeRowIndex: 0,
    completed: 0,
    total,
  });

  for (const [rowIndex, row] of rows.entries()) {
    const translatedRow = await translateRow(row, targetLanguage);
    translatedRows[rowIndex] = translatedRow;
    onRowTranslated?.(rowIndex, translatedRow);
    onProgress?.({
      activeRowIndex: rowIndex + 1 < total ? rowIndex + 1 : null,
      completed: rowIndex + 1,
      total,
    });
  }

  return translatedRows;
}
