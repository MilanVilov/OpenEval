import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listContainers } from '@/api/containers';
import type { Container } from '@/types/container';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Card } from '@/components/ui/card';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
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

  if (loading) return <LoadingSkeleton rows={3} />;
  if (error) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>;

  return (
    <PageTransition>
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
        <Card className="p-12 text-center animate-scale-in">
          <p className="text-foreground-secondary text-base">No containers yet.</p>
          <Link to="/containers/new"><Button className="mt-4" size="sm">Create your first container</Button></Link>
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
              {containers.map((container, idx) => (
                <TableRow
                  key={container.id}
                  className="animate-fade-in-up hover:bg-background-hover transition-colors duration-150"
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <TableCell>
                    <Link to={`/containers/${container.id}`} className="text-foreground-link hover:underline">{container.name}</Link>
                  </TableCell>
                  <TableCell className="tabular-nums">{container.file_count}</TableCell>
                  <TableCell>{formatDate(container.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </PageTransition>
  );
}
