import { useState } from 'react';
import { Badge } from '@/components/ui/badge';

interface TagFilterProps {
  allTags: string[];
  selectedTags: string[];
  onChange: (tags: string[]) => void;
}

const INITIAL_VISIBLE_TAGS = 40;

export function TagFilter({ allTags, selectedTags, onChange }: TagFilterProps) {
  const [showAll, setShowAll] = useState(false);

  if (allTags.length === 0) return null;

  function toggle(tag: string) {
    if (selectedTags.includes(tag)) {
      onChange(selectedTags.filter((t) => t !== tag));
    } else {
      onChange([...selectedTags, tag]);
    }
  }

  const visibleTags = showAll ? allTags : allTags.slice(0, INITIAL_VISIBLE_TAGS);
  const hiddenCount = allTags.length - visibleTags.length;

  return (
    <div className="mb-4 flex flex-wrap items-center gap-1.5">
      <span className="text-xs text-foreground-secondary uppercase tracking-wide mr-1">Tags</span>
      {visibleTags.map((tag) => (
        <button key={tag} type="button" onClick={() => toggle(tag)}>
          <Badge
            variant={selectedTags.includes(tag) ? 'info' : 'default'}
            className="cursor-pointer transition-colors"
          >
            {tag}
          </Badge>
        </button>
      ))}
      {hiddenCount > 0 && (
        <button
          type="button"
          onClick={() => setShowAll(true)}
          className="text-xs text-foreground-secondary hover:text-foreground transition-colors ml-1"
        >
          Show {hiddenCount} more
        </button>
      )}
      {selectedTags.length > 0 && (
        <button
          type="button"
          onClick={() => onChange([])}
          className="text-xs text-foreground-secondary hover:text-foreground transition-colors ml-1"
        >
          Clear
        </button>
      )}
    </div>
  );
}
