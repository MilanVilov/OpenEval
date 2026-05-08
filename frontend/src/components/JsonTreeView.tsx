import { cn } from '@/lib/utils';

interface JsonTreeViewProps {
  value: unknown;
  className?: string;
  defaultExpandedDepth?: number;
}

export function JsonTreeView({
  value,
  className,
  defaultExpandedDepth = 2,
}: JsonTreeViewProps) {
  return (
    <div
      className={cn(
        'rounded-md border border-border bg-background-secondary/50 p-3 font-mono text-xs',
        className,
      )}
    >
      <JsonTreeNode
        value={value}
        depth={0}
        path="$"
        name={null}
        defaultExpandedDepth={defaultExpandedDepth}
      />
    </div>
  );
}

interface JsonTreeNodeProps {
  value: unknown;
  depth: number;
  path: string;
  name: string | null;
  defaultExpandedDepth: number;
}

function JsonTreeNode({
  value,
  depth,
  path,
  name,
  defaultExpandedDepth,
}: JsonTreeNodeProps) {
  if (Array.isArray(value)) {
    return (
      <details open={depth < defaultExpandedDepth}>
        <summary className="cursor-pointer list-none text-foreground">
          <span className="mr-2 text-foreground-secondary">{name ? `${name}:` : ''}</span>
          <span className="text-accent-foreground">[{value.length}]</span>
          <span className="ml-2 text-foreground-secondary">{summarizeContainer(value)}</span>
        </summary>
        <div className="mt-2 space-y-1 border-l border-border pl-4">
          {value.map((item, index) => (
            <JsonTreeNode
              key={`${path}[${index}]`}
              value={item}
              depth={depth + 1}
              path={`${path}[${index}]`}
              name={`[${index}]`}
              defaultExpandedDepth={defaultExpandedDepth}
            />
          ))}
        </div>
      </details>
    );
  }

  if (isPlainObject(value)) {
    const entries = Object.entries(value);
    return (
      <details open={depth < defaultExpandedDepth}>
        <summary className="cursor-pointer list-none text-foreground">
          <span className="mr-2 text-foreground-secondary">{name ? `${name}:` : ''}</span>
          <span className="text-accent-foreground">{'{'}{entries.length}{'}'}</span>
          <span className="ml-2 text-foreground-secondary">{summarizeContainer(value)}</span>
        </summary>
        <div className="mt-2 space-y-1 border-l border-border pl-4">
          {entries.map(([key, childValue]) => (
            <JsonTreeNode
              key={`${path}.${key}`}
              value={childValue}
              depth={depth + 1}
              path={`${path}.${key}`}
              name={key}
              defaultExpandedDepth={defaultExpandedDepth}
            />
          ))}
        </div>
      </details>
    );
  }

  return (
    <div className="break-words text-foreground">
      {name ? <span className="mr-2 text-foreground-secondary">{name}:</span> : null}
      <span className={primitiveClassName(value)}>{formatPrimitive(value)}</span>
    </div>
  );
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function summarizeContainer(value: Record<string, unknown> | unknown[]): string {
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return 'empty array';
    }
    return `items ${value
      .slice(0, 3)
      .map((item) => summarizePreview(item))
      .join(', ')}${value.length > 3 ? ', ...' : ''}`;
  }

  const keys = Object.keys(value);
  if (keys.length === 0) {
    return 'empty object';
  }
  return `keys ${keys.slice(0, 4).join(', ')}${keys.length > 4 ? ', ...' : ''}`;
}

function summarizePreview(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.length}]`;
  }
  if (isPlainObject(value)) {
    return `{${Object.keys(value).length}}`;
  }
  return formatPrimitive(value);
}

function formatPrimitive(value: unknown): string {
  if (typeof value === 'string') {
    return JSON.stringify(value);
  }
  if (value === null) {
    return 'null';
  }
  return String(value);
}

function primitiveClassName(value: unknown): string {
  if (typeof value === 'string') {
    return 'text-success';
  }
  if (typeof value === 'number') {
    return 'text-info';
  }
  if (typeof value === 'boolean') {
    return 'text-warning';
  }
  if (value === null) {
    return 'text-foreground-disabled';
  }
  return 'text-foreground';
}
