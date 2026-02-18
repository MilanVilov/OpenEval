import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listVectorStores } from '@/api/vectorStores';
import type { VectorStore } from '@/types/vectorStore';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Plus } from 'lucide-react';
import { formatDate } from '@/lib/utils';

export function VectorStoreList() {
  const [stores, setStores] = useState<VectorStore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listVectorStores()
      .then(setStores)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton className="h-40 w-full" />;
  if (error) return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;

  return (
    <div>
      <PageHeader
        title="Vector Stores"
        description="Manage OpenAI vector stores"
        action={
          <Link to="/vector-stores/new">
            <Button size="sm"><Plus className="mr-2 h-4 w-4" />New Vector Store</Button>
          </Link>
        }
      />

      {stores.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-foreground-secondary">No vector stores yet.</p>
          <Link to="/vector-stores/new"><Button className="mt-4" size="sm">Create your first vector store</Button></Link>
        </Card>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Files</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {stores.map((store) => (
              <TableRow key={store.id}>
                <TableCell>
                  <Link to={`/vector-stores/${store.id}`} className="text-accent-blue hover:underline">{store.name}</Link>
                </TableCell>
                <TableCell>{store.file_count}</TableCell>
                <TableCell>{formatDate(store.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
