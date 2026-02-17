import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface StaggeredListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => ReactNode;
  keyExtractor: (item: T, index: number) => string | number;
  staggerMs?: number;
  className?: string;
}

/** Renders a list of items with staggered fade-in-up entrance animations. */
export function StaggeredList<T>({
  items,
  renderItem,
  keyExtractor,
  staggerMs = 60,
  className,
}: StaggeredListProps<T>) {
  return (
    <div className={cn(className)}>
      {items.map((item, index) => (
        <div
          key={keyExtractor(item, index)}
          className="animate-fade-in-up"
          style={{ animationDelay: `${index * staggerMs}ms` }}
        >
          {renderItem(item, index)}
        </div>
      ))}
    </div>
  );
}
