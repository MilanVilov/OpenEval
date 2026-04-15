import { Badge } from '@/components/ui/badge';

interface TagFilterProps {
  allTags: string[];
  selectedTags: string[];
  onChange: (tags: string[]) => void;
}

export function TagFilter({ allTags, selectedTags, onChange }: TagFilterProps) {
  if (allTags.length === 0) return null;

  function toggle(tag: string) {
    if (selectedTags.includes(tag)) {
      onChange(selectedTags.filter((t) => t !== tag));
    } else {
      onChange([...selectedTags, tag]);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-xs text-foreground-secondary uppercase tracking-wide mr-1">Tags</span>
      {allTags.map((tag) => (
        <button key={tag} type="button" onClick={() => toggle(tag)}>
          <Badge
            variant={selectedTags.includes(tag) ? 'info' : 'default'}
            className="cursor-pointer transition-colors"
          >
            {tag}
          </Badge>
        </button>
      ))}
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
