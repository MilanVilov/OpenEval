import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getDataset, deleteDataset, updateDatasetRows } from '@/api/datasets';
import type { DatasetDetail as DatasetDetailType } from '@/types/dataset';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
import { Spinner } from '@/components/Spinner';
import { formatDate } from '@/lib/utils';
import { Trash2, Save, Plus, X } from 'lucide-react';

export function DatasetDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState<DatasetDetailType | null>(null);
  const [rows, setRows] = useState<Record<string, string>[]>([]);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingCell, setEditingCell] = useState<{ row: number; col: string } | null>(null);

  useEffect(() => {
    if (!id) return;
    getDataset(id)
      .then((d) => {
        setDataset(d);
        setRows(d.rows);
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
    setDirty(true);
  }, []);

  function addRow() {
    if (!dataset) return;
    const empty: Record<string, string> = {};
    for (const col of dataset.columns) {
      empty[col] = '';
    }
    setRows((prev) => [...prev, empty]);
    setDirty(true);
  }

  function removeRow(idx: number) {
    setRows((prev) => prev.filter((_, i) => i !== idx));
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

  if (loading) return <LoadingSkeleton rows={5} />;
  if (error && !dataset) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>;
  if (!dataset) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>Dataset not found</AlertDescription></Alert>;

  const columns = dataset.columns as string[];

  return (
    <PageTransition>
      <PageHeader
        title={dataset.name}
        description={`${rows.length} rows · Created ${formatDate(dataset.created_at)}`}
        action={
          <div className="flex gap-2">
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
          <CardTitle>Dataset Rows</CardTitle>
          <Button size="sm" variant="outline" onClick={addRow}>
            <Plus className="mr-2 h-4 w-4" />Add Row
          </Button>
        </CardHeader>
        <CardContent>
          {columns.length === 0 ? (
            <p className="text-foreground-secondary text-sm">No columns available</p>
          ) : (
            <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10 text-center">#</TableHead>
                    {columns.map((col) => (
                      <TableHead key={col}>{col}</TableHead>
                    ))}
                    <TableHead className="w-10" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row, rowIdx) => (
                    <TableRow key={rowIdx}>
                      <TableCell className="text-center text-foreground-secondary text-xs">{rowIdx + 1}</TableCell>
                      {columns.map((col) => {
                        const isEditing = editingCell?.row === rowIdx && editingCell?.col === col;
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
                                onChange={(e) => updateCell(rowIdx, col, e.target.value)}
                                onBlur={() => setEditingCell(null)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Escape') setEditingCell(null);
                                }}
                              />
                            ) : (
                              <div
                                className="px-2 py-1.5 min-h-[32px] cursor-pointer hover:bg-background-secondary whitespace-pre-wrap break-words max-w-[400px] text-sm"
                                onClick={() => setEditingCell({ row: rowIdx, col })}
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
                          onClick={() => removeRow(rowIdx)}
                          title="Remove row"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </PageTransition>
  );
}
