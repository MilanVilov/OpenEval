import { Card } from '@/components/ui/card';

interface StatCardProps {
  label: string;
  value: string | number;
}

export function StatCard({ label, value }: StatCardProps) {
  return (
    <Card className="text-center p-4">
      <div className="text-2xl font-semibold text-foreground">{value}</div>
      <div className="text-xs font-medium uppercase tracking-wide text-foreground-secondary mt-1">
        {label}
      </div>
    </Card>
  );
}
