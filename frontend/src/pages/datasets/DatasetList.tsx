import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listDatasets } from '@/api/datasets';
import type { Dataset } from '@/types/dataset';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
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

  if (loading) return <LoadingSkeleton rows={4} />;
  if (error) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>;

  return (
    <PageTransition>
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
        <Card className="p-12 text-center animate-scale-in">
          <p className="text-foreground-secondary text-base">No datasets yet.</p>
          <Link to="/datasets/new"><Button className="mt-4" size="sm">Upload your first dataset</Button></Link>
        </Card>
      ) : (
        <div className="animate-fade-in">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Rows</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {datasets.map((ds, idx) => (
                <TableRow
                  key={ds.id}
                  className="animate-fade-in-up hover:bg-background-hover transition-colors duration-150"
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <TableCell>
                    <Link to={`/datasets/${ds.id}`} className="text-foreground-link hover:underline">{ds.name}</Link>
                  </TableCell>
                  <TableCell className="tabular-nums">{ds.row_count}</TableCell>
                  <TableCell>{formatDate(ds.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </PageTransition>
  );
}
