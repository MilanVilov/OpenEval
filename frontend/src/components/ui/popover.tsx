import { useState, useRef, useEffect, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface PopoverProps {
  trigger: ReactNode;
  children: ReactNode;
  className?: string;
  align?: 'start' | 'center' | 'end';
}

export function Popover({ trigger, children, className, align = 'center' }: PopoverProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [open]);

  const alignClass = align === 'start' ? 'left-0' : align === 'end' ? 'right-0' : 'left-1/2 -translate-x-1/2';

  return (
    <div ref={ref} className="relative h-full">
      <div onClick={() => setOpen(!open)} className="cursor-pointer h-full">
        {trigger}
      </div>
      {open && (
        <div
          className={cn(
            'absolute z-50 mt-2 rounded-md border border-border bg-background-card p-3 shadow-medium animate-fade-in',
            alignClass,
            className,
          )}
        >
          {children}
        </div>
      )}
    </div>
  );
}
