import type { ReactNode } from 'react';
import { useAnimateOnMount } from '@/hooks/useAnimateOnMount';
import { cn } from '@/lib/utils';

interface PageHeaderProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  const visible = useAnimateOnMount();

  return (
    <div
      className={cn(
        'flex items-center justify-between mb-8 transition-all duration-500 ease-[var(--ease-out-expo)]',
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3',
      )}
    >
      <div>
        <h1 className="text-xl font-semibold text-foreground tracking-tight">{title}</h1>
        {description && (
          <p className="text-sm text-foreground-secondary mt-1">{description}</p>
        )}
      </div>
      {action && (
        <div className="animate-fade-in" style={{ animationDelay: '150ms' }}>
          {action}
        </div>
      )}
    </div>
  );
}
