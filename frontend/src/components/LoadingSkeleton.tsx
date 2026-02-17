import { cn } from '@/lib/utils';

interface LoadingSkeletonProps {
  /** Number of skeleton rows to show */
  rows?: number;
  className?: string;
}

/** Multi-row shimmer loading skeleton for page content. */
export function LoadingSkeleton({ rows = 3, className }: LoadingSkeletonProps) {
  return (
    <div className={cn('space-y-3 animate-fade-in', className)}>
      {/* Title skeleton */}
      <div className="h-6 w-48 rounded-md bg-gradient-to-r from-background-card via-background-hover to-background-card animate-shimmer" />
      <div className="h-4 w-32 rounded-md bg-gradient-to-r from-background-card via-background-hover to-background-card animate-shimmer" style={{ animationDelay: '100ms' }} />

      <div className="mt-4 space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            className="h-12 w-full rounded-md bg-gradient-to-r from-background-card via-background-hover to-background-card animate-shimmer"
            style={{ animationDelay: `${(i + 2) * 75}ms` }}
          />
        ))}
      </div>
    </div>
  );
}
