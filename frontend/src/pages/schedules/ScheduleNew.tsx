import { useNavigate } from 'react-router-dom';
import { createSchedule } from '@/api/schedules';
import type { ScheduleCreateRequest, ScheduleFormData } from '@/types/schedule';
import { PageHeader } from '@/components/PageHeader';
import { PageTransition } from '@/components/PageTransition';
import { ScheduleForm } from '@/pages/schedules/ScheduleForm';

export function ScheduleNew() {
  const navigate = useNavigate();

  async function handleSubmit(data: ScheduleFormData): Promise<void> {
    const payload: ScheduleCreateRequest = {
      ...data,
      slack_webhook_url: data.slack_webhook_url ?? null,
    };
    await createSchedule(payload);
    navigate(`/schedules`);
  }

  return (
    <PageTransition>
      <PageHeader title="New Schedule" description="Run evaluations on a recurring schedule" />
      <ScheduleForm
        submitLabel="Create Schedule"
        onSubmit={handleSubmit}
        onCancel={() => navigate('/schedules')}
      />
    </PageTransition>
  );
}
