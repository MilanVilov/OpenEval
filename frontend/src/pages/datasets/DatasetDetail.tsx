import { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { deleteDataset, exportDataset, getDataset, updateDatasetRows } from '@/api/datasets';
import { translateInputColumn } from '@/api/dataSources';
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
import { formatDate } from '@/lib/utils';
import type { DatasetDetail as DatasetDetailType, DatasetRow } from '@/types/dataset';
import { Download, Plus, Save, Trash2, X } from 'lucide-react';

interface DatasetTranslationState {
  page: number;
  pageSize: number;
  originalInputs: string[];
  originalInputRowIndexes: number[];
  targetLanguage: string;
  translatedInputs: string[];
}

const DEFAULT_PAGE_SIZE = 50;

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
    if (col === 'input') {
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
    setError(null);
    try {
      const currentRows = currentPageRows.map((row) => ({ ...row }));
      const result = await translateInputColumn({
        target_language: targetLanguage.trim(),
        mapped_rows: currentRows,
      });
      setRows((current) => current.map((row, index) => {
        if (index < currentPageStart || index > currentPageEnd) {
          return row;
        }
        return result.mapped_rows[index - currentPageStart];
      }));
      setTranslationState({
        page,
        pageSize,
        originalInputs: currentRows.map((row) => row.input ?? ''),
        originalInputRowIndexes: [],
        targetLanguage: targetLanguage.trim(),
        translatedInputs: result.mapped_rows.map((row) => row.input ?? ''),
      });
      setDirty(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to translate the dataset page');
    } finally {
      setTranslating(false);
    }
  }

  function handleResetPageTranslation() {
    if (!currentPageTranslation) {
      return;
    }

    setRows((current) => current.map((row, index) => ({
      ...(index < currentPageStart || index > currentPageEnd
        ? row
        : {
            ...row,
            input: currentPageTranslation.originalInputs[index - currentPageStart] ?? row.input ?? '',
          }),
    })));
    setTranslationState(null);
    setDirty(true);
  }

  function toggleShowOriginalInput(rowIdx: number) {
    if (!currentPageTranslation) {
      return;
    }

    const showingOriginal = currentPageTranslation.originalInputRowIndexes.includes(rowIdx);
    const nextOriginalInputRowIndexes = showingOriginal
      ? currentPageTranslation.originalInputRowIndexes.filter((index) => index !== rowIdx)
      : [...currentPageTranslation.originalInputRowIndexes, rowIdx];
    const absoluteRowIndex = currentPageStart + rowIdx;

    setRows((current) => current.map((row, index) => (
      index === absoluteRowIndex
        ? {
            ...row,
            input: showingOriginal
              ? currentPageTranslation.translatedInputs[rowIdx] ?? row.input ?? ''
              : currentPageTranslation.originalInputs[rowIdx] ?? row.input ?? '',
          }
        : row
    )));
    setTranslationState({
      ...currentPageTranslation,
      originalInputRowIndexes: nextOriginalInputRowIndexes,
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
  const canTranslateInputColumn = columns.includes('input') && currentPageRows.length > 0;

  function handlePageChange(nextPage: number) {
    setEditingCell(null);
    setPage(nextPage);
  }

  function handlePageSizeChange(nextPageSize: number) {
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
            <Button variant="outline" size="sm" onClick={() => void handleExport()} disabled={downloading}>
              <Download className="mr-2 h-4 w-4" />
              {downloading ? 'Exporting...' : 'Export CSV'}
            </Button>
            {dataset.has_import_source ? (
              <Button variant="outline" size="sm" onClick={() => navigate(`/datasets/${dataset.id}/import`)}>
                Continue Import
              </Button>
            ) : null}
            {dirty && (
              <Button size="sm" onClick={handleSave} disabled={saving}>
                {saving ? <Spinner className="mr-2" /> : <Save className="mr-2 h-4 w-4" />}
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
            )}
            <Button variant="destructive" size="sm" onClick={handleDelete}>
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
          <Button size="sm" variant="outline" onClick={addRow}>
            <Plus className="mr-2 h-4 w-4" />Add Row
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {canTranslateInputColumn ? (
            <InputTranslationActions
              currentTranslationLanguage={translationState?.targetLanguage ?? null}
              loading={translating}
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
                    {currentPageTranslation ? <TableHead className="w-36">Input View</TableHead> : null}
                    {columns.map((col) => (
                      <TableHead key={col}>{col}</TableHead>
                    ))}
                    <TableHead className="w-10" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {currentPageRows.map((row, rowIdx) => {
                    const inputChanged = Boolean(
                      currentPageTranslation
                      && currentPageTranslation.originalInputs[rowIdx] !== currentPageTranslation.translatedInputs[rowIdx],
                    );
                    const showingOriginalInput = currentPageTranslation?.originalInputRowIndexes.includes(rowIdx) ?? false;
                    const absoluteRowIndex = currentPageStart + rowIdx;

                    return (
                      <TableRow key={absoluteRowIndex}>
                        <TableCell className="text-center text-foreground-secondary text-xs">{absoluteRowIndex + 1}</TableCell>
                        {currentPageTranslation ? (
                          <TableCell>
                            {inputChanged ? (
                              <Button
                                type="button"
                                variant={showingOriginalInput ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => toggleShowOriginalInput(rowIdx)}
                              >
                                {showingOriginalInput ? 'Original' : 'Translated'}
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
                                  className="px-2 py-1.5 min-h-[32px] cursor-pointer hover:bg-background-secondary whitespace-pre-wrap break-words max-w-[400px] text-sm"
                                  onClick={() => setEditingCell({ row: absoluteRowIndex, col })}
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
                            className="text-foreground-disabled hover:text-destructive p-1"
                            onClick={() => removeRow(absoluteRowIndex)}
                            title="Remove row"
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
