import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listVectorStores } from '@/api/vectorStores';
import type { VectorStore } from '@/types/vectorStore';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Card } from '@/components/ui/card';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
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

  if (loading) return <LoadingSkeleton rows={3} />;
  if (error) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>;

  return (
    <PageTransition>
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
        <Card className="p-12 text-center animate-scale-in">
          <p className="text-foreground-secondary text-base">No vector stores yet.</p>
          <Link to="/vector-stores/new"><Button className="mt-4" size="sm">Create your first vector store</Button></Link>
        </Card>
      ) : (
        <div className="animate-fade-in">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Files</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stores.map((store, idx) => (
                <TableRow
                  key={store.id}
                  className="animate-fade-in-up hover:bg-background-hover transition-colors duration-150"
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <TableCell>
                    <Link to={`/vector-stores/${store.id}`} className="text-foreground-link hover:underline">{store.name}</Link>
                  </TableCell>
                  <TableCell className="tabular-nums">{store.file_count}</TableCell>
                  <TableCell>{formatDate(store.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </PageTransition>
  );
}
