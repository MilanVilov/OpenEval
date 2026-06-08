import { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { deleteDataset, exportDataset, getDataset, updateDatasetRows } from '@/api/datasets';
import { translateMappedRows } from '@/api/dataSources';
import { InputTranslationActions } from '@/components/dataSources/InputTranslationActions';
import { ListPagination } from '@/components/ListControls';
import { PageHeader } from '@/components/PageHeader';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
import { Spinner } from '@/components/Spinner';
import {
  rowHasTranslatedChanges,
  toggleOriginalRowIndexes,
  type TranslatedPageState,
} from '@/lib/translatedPageRows';
import {
  translateRowsSequentially,
  type RowTranslationProgress,
} from '@/lib/translateRowsSequentially';
import { formatDate } from '@/lib/utils';
import type { DatasetDetail as DatasetDetailType, DatasetRow } from '@/types/dataset';
import { Download, Plus, Save, Trash2, X } from 'lucide-react';

interface DatasetTranslationState extends TranslatedPageState<DatasetRow> {
  page: number;
  pageSize: number;
}

const DEFAULT_PAGE_SIZE = 50;
const TRANSLATED_FIELDS = ['input', 'expected_output'];

function buildCurrentPageSourceRows(
  currentPageRows: DatasetRow[],
  currentPageTranslation: DatasetTranslationState | null,
): DatasetRow[] {
  return currentPageRows.map((row, index) => ({
    ...row,
    ...(currentPageTranslation?.originalRows[index] ?? row),
  }));
}

function replacePageRows(
  currentRows: DatasetRow[],
  pageStart: number,
  nextPageRows: DatasetRow[],
): DatasetRow[] {
  const updatedRows = [...currentRows];
  updatedRows.splice(pageStart, nextPageRows.length, ...nextPageRows);
  return updatedRows;
}

function buildTranslationErrorMessage(
  error: unknown,
  progress: RowTranslationProgress | null,
  fallbackMessage: string,
): string {
  const baseMessage = error instanceof Error ? error.message : fallbackMessage;
  if (!progress || progress.completed === 0) {
    return baseMessage;
  }
  return `${baseMessage} Translation stopped after ${progress.completed} of ${progress.total} rows.`;
}

export function DatasetDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState<DatasetDetailType | null>(null);
  const [rows, setRows] = useState<DatasetRow[]>([]);
  const [translationState, setTranslationState] = useState<DatasetTranslationState | null>(null);
  const [targetLanguage, setTargetLanguage] = useState('English');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [translationProgress, setTranslationProgress] = useState<RowTranslationProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingCell, setEditingCell] = useState<{ row: number; col: string } | null>(null);

  useEffect(() => {
    if (!id) return;
    getDataset(id)
      .then((d) => {
        setDataset(d);
        setRows(d.rows);
        setTranslationState(null);
        setTranslationProgress(null);
        setPage(1);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const updateCell = useCallback((rowIdx: number, col: string, value: string) => {
    setRows((prev) => {
      const updated = [...prev];
      updated[rowIdx] = { ...updated[rowIdx], [col]: value };
      return updated;
    });
    if (TRANSLATED_FIELDS.includes(col)) {
      setTranslationState(null);
    }
    setDirty(true);
  }, []);

  function addRow() {
    if (!dataset) return;
    const empty: DatasetRow = {};
    for (const col of dataset.columns) {
      empty[col] = '';
    }
    setRows((prev) => [...prev, empty]);
    setTranslationState(null);
    setDirty(true);
  }

  function removeRow(idx: number) {
    setRows((prev) => prev.filter((_, i) => i !== idx));
    setTranslationState(null);
    setDirty(true);
  }

  async function handleSave() {
    if (!id) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateDatasetRows(id, rows);
      setDataset(updated);
      setRows(updated.rows);
      setTranslationState(null);
      setDirty(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!id || !confirm('Delete this dataset?')) return;
    await deleteDataset(id);
    navigate('/datasets');
  }

  async function handleExport() {
    if (!id) return;
    setDownloading(true);
    setError(null);
    try {
      await exportDataset(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to export dataset');
    } finally {
      setDownloading(false);
    }
  }

  async function handleTranslatePage() {
    if (!currentPageRows.length) {
      setError('There are no rows on this page to translate.');
      return;
    }
    if (!targetLanguage.trim()) {
      setError('Enter a target language before translating this page.');
      return;
    }

    setTranslating(true);
    setEditingCell(null);
    setError(null);
    let latestProgress: RowTranslationProgress | null = null;
    try {
      const currentRows = buildCurrentPageSourceRows(currentPageRows, currentPageTranslation);

      setRows((current) => replacePageRows(current, currentPageStart, currentRows));
      setTranslationState({
        page: safePage,
        pageSize,
        originalRowIndexes: [],
        originalRows: currentRows,
        targetLanguage: targetLanguage.trim(),
        translatedRows: currentRows,
      });
      await translateRowsSequentially({
        rows: currentRows,
        targetLanguage: targetLanguage.trim(),
        translateRow: async (row, language) => {
          const result = await translateMappedRows({
            target_language: language,
            fields: TRANSLATED_FIELDS,
            mapped_rows: [row],
          });
          const translatedRow = result.mapped_rows[0];
          if (!translatedRow) {
            throw new Error('Translation response was empty for one of the rows.');
          }
          return translatedRow;
        },
        onProgress: (progress) => {
          latestProgress = progress;
          setTranslationProgress(progress);
        },
        onRowTranslated: (rowIndex, translatedRow) => {
          setRows((current) => current.map((row, index) => (
            index === currentPageStart + rowIndex ? translatedRow : row
          )));
          setTranslationState((current) => {
            if (!current || current.page !== safePage || current.pageSize !== pageSize) {
              return current;
            }
            const nextTranslatedRows = current.translatedRows.map((row, index) => (
              index === rowIndex ? translatedRow : row
            ));
            return {
              ...current,
              translatedRows: nextTranslatedRows,
            };
          });
          setDirty(true);
        },
      });
    } catch (e) {
      setError(buildTranslationErrorMessage(e, latestProgress, 'Failed to translate the dataset page'));
    } finally {
      setTranslating(false);
      setTranslationProgress(null);
    }
  }

  function handleResetPageTranslation() {
    if (!currentPageTranslation) {
      return;
    }

    setRows((current) => current.map((row, index) => ({
      ...(index < currentPageStart || index > currentPageEnd
        ? row
        : currentPageTranslation.originalRows[index - currentPageStart] ?? row),
    })));
    setTranslationState(null);
    setDirty(true);
  }

  function toggleShowOriginalRow(rowIdx: number) {
    if (!currentPageTranslation || translating) {
      return;
    }

    const showingOriginal = currentPageTranslation.originalRowIndexes.includes(rowIdx);
    const absoluteRowIndex = currentPageStart + rowIdx;
    const nextOriginalRowIndexes = toggleOriginalRowIndexes(
      currentPageTranslation.originalRowIndexes,
      rowIdx,
    );

    setRows((current) => current.map((row, index) => (
      index === absoluteRowIndex
        ? (
            showingOriginal
              ? currentPageTranslation.translatedRows[rowIdx] ?? row
              : currentPageTranslation.originalRows[rowIdx] ?? row
          )
        : row
    )));
    setTranslationState({
      ...currentPageTranslation,
      originalRowIndexes: nextOriginalRowIndexes,
    });
    setDirty(true);
  }

  if (loading) return <LoadingSkeleton rows={5} />;
  if (error && !dataset) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>;
  if (!dataset) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>Dataset not found</AlertDescription></Alert>;

  const columns = dataset.columns as string[];
  const pages = Math.max(1, Math.ceil(rows.length / pageSize));
  const safePage = Math.min(page, pages);
  const currentPageStart = (safePage - 1) * pageSize;
  const currentPageEnd = currentPageStart + pageSize - 1;
  const currentPageRows = rows.slice(currentPageStart, currentPageStart + pageSize);
  const currentPageTranslation = translationState?.page === safePage
    && translationState.pageSize === pageSize
      ? translationState
      : null;
  const canTranslatePageText = columns.includes('input') && currentPageRows.length > 0;

  function handlePageChange(nextPage: number) {
    if (translating) {
      return;
    }
    setEditingCell(null);
    setPage(nextPage);
  }

  function handlePageSizeChange(nextPageSize: number) {
    if (translating) {
      return;
    }
    setEditingCell(null);
    setPageSize(nextPageSize);
    setPage(1);
  }

  return (
    <PageTransition>
      <PageHeader
        title={dataset.name}
        description={`${rows.length} rows · Created ${formatDate(dataset.created_at)}`}
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => void handleExport()} disabled={downloading || translating}>
              <Download className="mr-2 h-4 w-4" />
              {downloading ? 'Exporting...' : 'Export CSV'}
            </Button>
            {dataset.has_import_source ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate(`/datasets/${dataset.id}/import`)}
                disabled={translating}
              >
                Continue Import
              </Button>
            ) : null}
            {dirty && (
              <Button size="sm" onClick={handleSave} disabled={saving || translating}>
                {saving ? <Spinner className="mr-2" /> : <Save className="mr-2 h-4 w-4" />}
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
            )}
            <Button variant="destructive" size="sm" onClick={handleDelete} disabled={translating}>
              <Trash2 className="mr-2 h-4 w-4" />Delete
            </Button>
          </div>
        }
      />

      {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Dataset Rows</CardTitle>
            <p className="mt-1 text-xs text-foreground-secondary">
              Export downloads the latest saved CSV exactly as this dataset will be evaluated.
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={addRow} disabled={translating}>
            <Plus className="mr-2 h-4 w-4" />Add Row
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {canTranslatePageText ? (
            <InputTranslationActions
              currentTranslationLanguage={currentPageTranslation?.targetLanguage ?? null}
              translatedFields={TRANSLATED_FIELDS}
              loading={translating}
              progress={translationProgress}
              targetLanguage={targetLanguage}
              onTargetLanguageChange={setTargetLanguage}
              onTranslate={() => void handleTranslatePage()}
              onReset={handleResetPageTranslation}
            />
          ) : null}

          {columns.length === 0 ? (
            <p className="text-foreground-secondary text-sm">No columns available</p>
          ) : (
            <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10 text-center">#</TableHead>
                    {currentPageTranslation ? <TableHead className="w-36">Text View</TableHead> : null}
                    {columns.map((col) => (
                      <TableHead key={col}>{col}</TableHead>
                    ))}
                    <TableHead className="w-10" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {currentPageRows.map((row, rowIdx) => {
                    const rowChanged = rowHasTranslatedChanges(currentPageTranslation, rowIdx, TRANSLATED_FIELDS);
                    const showingOriginalRow = currentPageTranslation?.originalRowIndexes.includes(rowIdx) ?? false;
                    const activeTranslationRowIndex = translationProgress?.activeRowIndex ?? null;
                    const activeTranslationRow = translating && activeTranslationRowIndex === rowIdx;
                    const pendingTranslationRow = translating
                      && activeTranslationRowIndex !== null
                      && rowIdx > activeTranslationRowIndex;
                    const absoluteRowIndex = currentPageStart + rowIdx;

                    return (
                      <TableRow key={absoluteRowIndex}>
                        <TableCell className="text-center text-foreground-secondary text-xs">{absoluteRowIndex + 1}</TableCell>
                        {currentPageTranslation ? (
                          <TableCell>
                            {activeTranslationRow ? (
                              <Badge variant="info" className="gap-1">
                                <Spinner className="h-3 w-3" />
                                Translating
                              </Badge>
                            ) : pendingTranslationRow ? (
                              <Badge>Pending</Badge>
                            ) : rowChanged ? (
                              <Button
                                type="button"
                                variant={showingOriginalRow ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => toggleShowOriginalRow(rowIdx)}
                                disabled={translating}
                              >
                                {showingOriginalRow ? 'Original' : 'Translated'}
                              </Button>
                            ) : (
                              <Badge>Same text</Badge>
                            )}
                          </TableCell>
                        ) : null}
                        {columns.map((col) => {
                          const isEditing = editingCell?.row === absoluteRowIndex && editingCell?.col === col;
                          return (
                            <TableCell
                              key={col}
                              className="p-0"
                            >
                              {isEditing ? (
                                <textarea
                                  autoFocus
                                  className="w-full min-w-[120px] bg-background-input border border-border-focus rounded px-2 py-1.5 text-sm resize-y focus:outline-none"
                                  value={row[col] ?? ''}
                                  rows={Math.max(2, (row[col] ?? '').split('\n').length)}
                                  onChange={(e) => updateCell(absoluteRowIndex, col, e.target.value)}
                                  onBlur={() => setEditingCell(null)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Escape') setEditingCell(null);
                                  }}
                                />
                              ) : (
                                <div
                                  className={`px-2 py-1.5 min-h-[32px] whitespace-pre-wrap break-words max-w-[400px] text-sm ${
                                    translating
                                      ? 'cursor-default'
                                      : 'cursor-pointer hover:bg-background-secondary'
                                  }`}
                                  onClick={() => {
                                    if (!translating) {
                                      setEditingCell({ row: absoluteRowIndex, col });
                                    }
                                  }}
                                  title="Click to edit"
                                >
                                  {row[col] || <span className="text-foreground-disabled italic">empty</span>}
                                </div>
                              )}
                            </TableCell>
                          );
                        })}
                        <TableCell className="p-1">
                          <button
                            className="text-foreground-disabled hover:text-destructive p-1 disabled:opacity-50"
                            onClick={() => removeRow(absoluteRowIndex)}
                            title="Remove row"
                            disabled={translating}
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}

          <ListPagination
            page={safePage}
            pageSize={pageSize}
            pages={pages}
            total={rows.length}
            itemLabel="rows"
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
          />
        </CardContent>
      </Card>
    </PageTransition>
  );
}
