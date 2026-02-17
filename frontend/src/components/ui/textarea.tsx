import { type TextareaHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          'flex w-full rounded border border-border bg-background-input px-3 py-2 text-sm text-foreground placeholder:text-foreground-disabled focus:outline-none focus:border-border-focus focus:ring-1 focus:ring-border-focus transition-colors duration-150 disabled:opacity-50 min-h-[80px]',
          className,
        )}
        {...props}
      />
    );
  },
);
Textarea.displayName = 'Textarea';
