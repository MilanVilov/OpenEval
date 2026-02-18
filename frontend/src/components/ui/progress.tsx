import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
}

export function Progress({ value, max = 100, className, ...props }: ProgressProps) {
  const percent = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div
      className={cn('h-1.5 w-full overflow-hidden rounded-full bg-background-input', className)}
      {...props}
    >
      <div
        className="h-full rounded-full bg-gradient-to-r from-accent to-accent-purple transition-all duration-300"
        style={{ width: `${percent}%` }}
      />
    </div>
  );
}
