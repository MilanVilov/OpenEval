import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { duplicateDataSource, listDataSources } from '@/api/dataSources';
import type { DataSource } from '@/types/dataSource';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageHeader } from '@/components/PageHeader';
import { PageTransition } from '@/components/PageTransition';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Copy, Plus } from 'lucide-react';
import { formatDate } from '@/lib/utils';

export function DataSourceList() {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [duplicatingId, setDuplicatingId] = useState<string | null>(null);

  useEffect(() => {
    listDataSources()
      .then(setSources)
      .catch((listError: Error) => setError(listError.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleDuplicate(sourceId: string) {
    setDuplicatingId(sourceId);
    setError(null);
    try {
      const duplicate = await duplicateDataSource(sourceId);
      setSources((current) => [duplicate, ...current]);
    } catch (duplicateError) {
      setError(duplicateError instanceof Error ? duplicateError.message : 'Failed to duplicate data source');
    } finally {
      setDuplicatingId(null);
    }
  }

  if (loading) return <LoadingSkeleton rows={4} />;
  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  return (
    <PageTransition>
      <PageHeader
        title="Data Sources"
        description="Manage reusable remote endpoints and their saved import mappings"
        action={(
          <Link to="/data-sources/new">
            <Button size="sm"><Plus className="mr-2 h-4 w-4" />New Source</Button>
          </Link>
        )}
      />

      {sources.length === 0 ? (
        <Card className="p-12 text-center animate-scale-in">
          <p className="text-base text-foreground-secondary">No data sources yet.</p>
          <Link to="/data-sources/new"><Button className="mt-4" size="sm">Create your first source</Button></Link>
        </Card>
      ) : (
        <div className="animate-fade-in">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Method</TableHead>
                <TableHead>Auth</TableHead>
                <TableHead>Pagination</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead className="w-16 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sources.map((source) => (
                <TableRow key={source.id} className="hover:bg-background-hover transition-colors duration-150">
                  <TableCell>
                    <Link to={`/data-sources/${source.id}`} className="text-foreground-link hover:underline">
                      {source.name}
                    </Link>
                  </TableCell>
                  <TableCell>{source.method}</TableCell>
                  <TableCell>{source.auth_type}</TableCell>
                  <TableCell>{source.pagination_mode}</TableCell>
                  <TableCell>{formatDate(source.updated_at || source.created_at)}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0"
                      disabled={duplicatingId === source.id}
                      onClick={() => void handleDuplicate(source.id)}
                      title="Duplicate data source"
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </PageTransition>
  );
}
