import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getDataset, deleteDataset } from '@/api/datasets';
import type { DatasetDetail as DatasetDetailType } from '@/types/dataset';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { formatDate } from '@/lib/utils';
import { Trash2 } from 'lucide-react';

export function DatasetDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState<DatasetDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getDataset(id)
      .then(setDataset)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleDelete() {
    if (!id || !confirm('Delete this dataset?')) return;
    await deleteDataset(id);
    navigate('/datasets');
  }

  if (loading) return <Skeleton className="h-60 w-full" />;
  if (error) return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;
  if (!dataset) return <Alert variant="destructive"><AlertDescription>Dataset not found</AlertDescription></Alert>;

  const previewColumns = dataset.preview.length > 0 ? Object.keys(dataset.preview[0]) : [];

  return (
    <div>
      <PageHeader
        title={dataset.name}
        description={`${dataset.row_count} rows · Created ${formatDate(dataset.created_at)}`}
        action={
          <Button variant="destructive" size="sm" onClick={handleDelete}>
            <Trash2 className="mr-2 h-4 w-4" />Delete
          </Button>
        }
      />

      <Card>
        <CardHeader><CardTitle>Preview (first rows)</CardTitle></CardHeader>
        <CardContent>
          {previewColumns.length === 0 ? (
            <p className="text-foreground-secondary text-sm">No preview available</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    {previewColumns.map((col) => (
                      <TableHead key={col}>{col}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dataset.preview.map((row, i) => (
                    <TableRow key={i}>
                      {previewColumns.map((col) => (
                        <TableCell key={col} className="max-w-[300px] truncate">
                          {row[col]}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
