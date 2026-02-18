import { type InputHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          'flex h-9 w-full rounded border border-border bg-background-input px-3 py-2 text-sm text-foreground placeholder:text-foreground-disabled focus:outline-none focus:border-border-focus focus:ring-1 focus:ring-border-focus transition-colors duration-150 disabled:opacity-50',
          className,
        )}
        {...props}
      />
    );
  },
);
Input.displayName = 'Input';
