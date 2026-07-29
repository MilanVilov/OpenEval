import {
  type ReactNode,
  useId,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { hasClampedOverflow } from '@/lib/expandableCell';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface ExpandableCellProps {
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}

/** Render table-cell content clamped to four lines with an accessible expansion control. */
export function ExpandableCell({
  children,
  className,
  contentClassName,
}: ExpandableCellProps) {
  const contentId = useId();
  const contentRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [canExpand, setCanExpand] = useState(false);

  useLayoutEffect(() => {
    const content = contentRef.current;
    if (!content || expanded) return;

    const measure = () => setCanExpand(hasClampedOverflow(content));
    measure();

    const observer = new ResizeObserver(measure);
    observer.observe(content);
    return () => observer.disconnect();
  }, [children, expanded]);

  return (
    <div className={cn('min-w-0', className)}>
      <div
        id={contentId}
        ref={contentRef}
        className={cn(
          'whitespace-pre-wrap break-words',
          expanded ? 'max-h-[60vh] overflow-y-auto pr-2' : 'line-clamp-4',
          contentClassName,
        )}
      >
        {children}
      </div>
      {canExpand ? (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="mt-1 h-6 gap-1 px-1 text-foreground-link hover:bg-accent-muted"
          aria-controls={contentId}
          aria-expanded={expanded}
          onClick={(event) => {
            event.stopPropagation();
            setExpanded((current) => !current);
          }}
        >
          {expanded ? (
            <ChevronUp className="h-3 w-3" aria-hidden="true" />
          ) : (
            <ChevronDown className="h-3 w-3" aria-hidden="true" />
          )}
          {expanded ? 'Show less' : 'Show more'}
        </Button>
      ) : null}
    </div>
  );
}
