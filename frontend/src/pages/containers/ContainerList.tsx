import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listContainers } from '@/api/containers';
import type { Container } from '@/types/container';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Plus } from 'lucide-react';
import { formatDate } from '@/lib/utils';

export function ContainerList() {
  const [containers, setContainers] = useState<Container[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listContainers()
      .then(setContainers)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton className="h-40 w-full" />;
  if (error) return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;

  return (
    <div>
      <PageHeader
        title="Containers"
        description="Manage OpenAI containers for the shell tool"
        action={
          <Link to="/containers/new">
            <Button size="sm"><Plus className="mr-2 h-4 w-4" />New Container</Button>
          </Link>
        }
      />

      {containers.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-foreground-secondary">No containers yet.</p>
          <Link to="/containers/new"><Button className="mt-4" size="sm">Create your first container</Button></Link>
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
            {containers.map((container) => (
              <TableRow key={container.id}>
                <TableCell>
                  <Link to={`/containers/${container.id}`} className="text-accent-blue hover:underline">{container.name}</Link>
                </TableCell>
                <TableCell>{container.file_count}</TableCell>
                <TableCell>{formatDate(container.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
