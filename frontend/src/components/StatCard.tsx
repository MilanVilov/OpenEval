import type { ReactNode } from 'react';
import { Card } from '@/components/ui/card';
import { useCountUp } from '@/hooks/useCountUp';

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: ReactNode;
}

export function StatCard({ label, value, icon }: StatCardProps) {
  // Animate numeric values
  const numericValue = typeof value === 'number' ? value : parseFloat(value);
  const isAnimatable = !isNaN(numericValue) && Number.isInteger(numericValue) && numericValue >= 0;
  const animated = useCountUp(isAnimatable ? numericValue : 0);

  return (
    <Card className="relative text-center p-4 transition-all duration-200 hover:shadow-medium hover:border-border-hover overflow-hidden h-full flex flex-col justify-center">
      {icon && <span className="absolute top-2 right-2">{icon}</span>}
      <div
        className={`font-semibold text-foreground tabular-nums ${
          isAnimatable ? 'text-2xl' : 'text-sm font-mono truncate'
        }`}
        title={String(value)}
      >
        {isAnimatable ? animated : value}
      </div>
      <div className="text-xs font-medium uppercase tracking-wide text-foreground-secondary mt-1.5">
        {label}
      </div>
    </Card>
  );
}
