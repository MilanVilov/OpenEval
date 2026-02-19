import type { ReactNode } from 'react';

interface PageTransitionProps {
  children: ReactNode;
}

/** Wraps page content with a smooth fade-in-up entrance animation. */
export function PageTransition({ children }: PageTransitionProps) {
  return (
    <div className="animate-fade-in-up" style={{ animationDuration: '350ms' }}>
      {children}
    </div>
  );
}
