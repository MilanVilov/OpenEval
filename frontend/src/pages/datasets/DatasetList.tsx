import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listDatasets } from '@/api/datasets';
import type { Dataset } from '@/types/dataset';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Plus } from 'lucide-react';
import { formatDate } from '@/lib/utils';

export function DatasetList() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listDatasets()
      .then(setDatasets)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton className="h-40 w-full" />;
  if (error) return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;

  return (
    <div>
      <PageHeader
        title="Datasets"
        description="Manage evaluation datasets"
        action={
          <Link to="/datasets/new">
            <Button size="sm"><Plus className="mr-2 h-4 w-4" />Upload Dataset</Button>
          </Link>
        }
      />

      {datasets.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-foreground-secondary">No datasets yet.</p>
          <Link to="/datasets/new"><Button className="mt-4" size="sm">Upload your first dataset</Button></Link>
        </Card>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Rows</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {datasets.map((ds) => (
              <TableRow key={ds.id}>
                <TableCell>
                  <Link to={`/datasets/${ds.id}`} className="text-accent-blue hover:underline">{ds.name}</Link>
                </TableCell>
                <TableCell>{ds.row_count}</TableCell>
                <TableCell>{formatDate(ds.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
