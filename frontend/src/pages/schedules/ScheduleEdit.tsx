import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getSchedule, updateSchedule } from '@/api/schedules';
import type { Schedule, ScheduleFormData } from '@/types/schedule';
import { PageHeader } from '@/components/PageHeader';
import { PageTransition } from '@/components/PageTransition';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScheduleForm } from '@/pages/schedules/ScheduleForm';

export function ScheduleEdit() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getSchedule(id)
      .then(setSchedule)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleSubmit(data: ScheduleFormData): Promise<void> {
    if (!id) return;
    await updateSchedule(id, data);
    navigate('/schedules');
  }

  if (loading) return <LoadingSkeleton rows={4} />;
  if (error) return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;
  if (!schedule) return null;

  return (
    <PageTransition>
      <PageHeader title="Edit Schedule" description={schedule.name} />
      <ScheduleForm
        initial={schedule}
        submitLabel="Save Changes"
        onSubmit={handleSubmit}
        onCancel={() => navigate('/schedules')}
      />
    </PageTransition>
  );
}
