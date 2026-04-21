import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  deleteSchedule,
  listSchedules,
  runScheduleNow,
  toggleSchedule,
} from '@/api/schedules';
import type { Schedule } from '@/types/schedule';
import { PageHeader } from '@/components/PageHeader';
import { PageTransition } from '@/components/PageTransition';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from '@/components/ui/table';
import { StatusBadge } from '@/components/StatusBadge';
import { Plus, Play, Pencil, Trash2 } from 'lucide-react';
import { describeCron } from '@/lib/cron';
import { formatDate, formatPercent } from '@/lib/utils';

export function ScheduleList() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => { void load(); }, []);

  async function load(): Promise<void> {
    setLoading(true);
    try {
      setSchedules(await listSchedules());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load schedules');
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle(id: string): Promise<void> {
    setBusyId(id);
    try { await toggleSchedule(id); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Failed to toggle'); }
    finally { setBusyId(null); }
  }

  async function handleRunNow(id: string): Promise<void> {
    setBusyId(id);
    try { await runScheduleNow(id); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Failed to start run'); }
    finally { setBusyId(null); }
  }

  async function handleDelete(id: string): Promise<void> {
    if (!window.confirm('Delete this schedule? Past runs it created will be kept.')) return;
    setBusyId(id);
    try { await deleteSchedule(id); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Failed to delete'); }
    finally { setBusyId(null); }
  }

  if (loading) return <LoadingSkeleton rows={5} />;

  return (
    <PageTransition>
      <PageHeader
        title="Schedules"
        description="Recurring evaluation runs with optional Slack notifications"
        action={
          <Link to="/schedules/new">
            <Button size="sm"><Plus className="mr-2 h-4 w-4" />New Schedule</Button>
          </Link>
        }
      />

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {schedules.length === 0 ? (
        <Card className="p-12 text-center animate-scale-in">
          <p className="text-foreground-secondary text-base">No schedules yet.</p>
          <Link to="/schedules/new">
            <Button className="mt-4" size="sm">Create your first schedule</Button>
          </Link>
        </Card>
      ) : (
        <div className="animate-fade-in">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Schedule</TableHead>
                <TableHead>Config / Dataset</TableHead>
                <TableHead>Last run</TableHead>
                <TableHead>Next run</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-48 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {schedules.map((s) => (
                <TableRow key={s.id} className="hover:bg-background-hover">
                  <TableCell className="font-medium">
                    <Link to={`/schedules/${s.id}/edit`} className="text-foreground-link hover:underline">
                      {s.name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">{describeCron(s.cron_expression)}</div>
                    <code className="text-xs text-foreground-secondary font-mono">{s.cron_expression}</code>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">{s.config_name ?? '—'}</div>
                    <div className="text-xs text-foreground-secondary">{s.dataset_name ?? '—'}</div>
                  </TableCell>
                  <TableCell>
                    {s.last_run ? (
                      <Link to={`/runs/${s.last_run.id}`} className="block text-foreground-link hover:underline">
                        <StatusBadge status={s.last_run.status} />
                        <span className="block text-xs text-foreground-secondary tabular-nums">
                          {s.last_run.accuracy != null ? formatPercent(s.last_run.accuracy) : '—'}
                        </span>
                      </Link>
                    ) : (<span className="text-foreground-secondary">—</span>)}
                  </TableCell>
                  <TableCell className="text-sm tabular-nums">
                    {s.enabled && s.next_run_at ? formatDate(s.next_run_at) : '—'}
                  </TableCell>
                  <TableCell>
                    <Badge variant={s.enabled ? 'success' : 'default'}>
                      {s.enabled ? 'Enabled' : 'Disabled'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost" size="sm"
                        disabled={busyId === s.id}
                        onClick={() => void handleRunNow(s.id)}
                        aria-label="Run now"
                        title="Run now"
                      >
                        <Play className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost" size="sm"
                        disabled={busyId === s.id}
                        onClick={() => void handleToggle(s.id)}
                        title={s.enabled ? 'Disable' : 'Enable'}
                      >
                        {s.enabled ? 'Disable' : 'Enable'}
                      </Button>
                      <Link to={`/schedules/${s.id}/edit`}>
                        <Button variant="ghost" size="sm" aria-label="Edit schedule" title="Edit"><Pencil className="h-4 w-4" /></Button>
                      </Link>
                      <Button
                        variant="ghost" size="sm"
                        disabled={busyId === s.id}
                        onClick={() => void handleDelete(s.id)}
                        aria-label="Delete schedule"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
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
