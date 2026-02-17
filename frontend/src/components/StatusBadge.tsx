import { Badge } from '@/components/ui/badge';

interface StatusBadgeProps {
  status: string;
}

const statusVariant: Record<string, 'success' | 'error' | 'warning' | 'info' | 'default'> = {
  completed: 'success',
  passed: 'success',
  failed: 'error',
  running: 'warning',
  pending: 'info',
  creating: 'info',
  ready: 'success',
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <Badge variant={statusVariant[status] ?? 'default'}>
      {status}
    </Badge>
  );
}
