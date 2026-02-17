import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { cn } from '@/lib/utils';
import { useState, useEffect, useCallback } from 'react';
import { Check, Copy, Maximize2, Minimize2 } from 'lucide-react';

interface CodeBlockProps {
  /** The code string to display. Objects will be auto-stringified. */
  code: string | object;
  /** Language for syntax highlighting. Defaults to 'json'. */
  language?: string;
  /** Max height before scrolling. Defaults to '400px'. */
  maxHeight?: string;
  /** Show a maximize button to expand to full-screen overlay. */
  expandable?: boolean;
  /** Title shown in the expanded overlay header. */
  expandTitle?: string;
  className?: string;
}

/** Custom dark theme matching project palette */
const customTheme = {
  ...oneDark,
  'pre[class*="language-"]': {
    ...oneDark['pre[class*="language-"]'],
    background: '#1c1c28',
    margin: 0,
    borderRadius: '6px',
    fontSize: '12px',
    lineHeight: '1.6',
  },
  'code[class*="language-"]': {
    ...oneDark['code[class*="language-"]'],
    background: 'transparent',
    fontSize: '12px',
    lineHeight: '1.6',
  },
};

/** Highlighted code block with copy button, suitable for JSON and other formats. */
export function CodeBlock({ code, language = 'json', maxHeight = '400px', expandable = false, expandTitle, className }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const codeStr = typeof code === 'string' ? code : JSON.stringify(code, null, 2);

  async function handleCopy() {
    await navigator.clipboard.writeText(codeStr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') setExpanded(false);
  }, []);

  useEffect(() => {
    if (expanded) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [expanded, handleEscape]);

  function renderHighlighter(height?: string) {
    return (
      <div style={height ? { maxHeight: height } : undefined} className={cn('overflow-auto', !height && 'h-full')}>
        <SyntaxHighlighter
          language={language}
          style={customTheme}
          showLineNumbers={codeStr.split('\n').length > 5}
          lineNumberStyle={{ color: '#4a4a5c', fontSize: '11px', minWidth: '2.5em' }}
          wrapLongLines
        >
          {codeStr}
        </SyntaxHighlighter>
      </div>
    );
  }

  return (
    <>
      <div className={cn('relative group rounded-md border border-border-muted overflow-hidden', className)}>
        <div className="absolute right-2 top-2 z-10 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          {expandable && (
            <button
              type="button"
              onClick={() => setExpanded(true)}
              className="p-1.5 rounded bg-background-hover/80 text-foreground-secondary hover:text-foreground transition-colors duration-150"
              title="Expand"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
          )}
          <button
            type="button"
            onClick={handleCopy}
            className="p-1.5 rounded bg-background-hover/80 text-foreground-secondary hover:text-foreground transition-colors duration-150"
            title="Copy to clipboard"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
        </div>
        {renderHighlighter(maxHeight)}
      </div>

      {/* Full-screen overlay */}
      {expanded && (
        <div
          className="fixed inset-0 z-50 flex flex-col bg-background/95 backdrop-blur-sm animate-fade-in"
          onClick={() => setExpanded(false)}
        >
          <div
            className="flex flex-col h-full max-w-5xl w-full mx-auto p-6 animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-4 shrink-0">
              <h2 className="text-sm font-medium text-foreground">
                {expandTitle ?? 'Code'}
              </h2>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={handleCopy}
                  className="p-1.5 rounded text-foreground-secondary hover:text-foreground hover:bg-background-hover transition-colors duration-150"
                  title="Copy to clipboard"
                >
                  {copied ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
                </button>
                <button
                  type="button"
                  onClick={() => setExpanded(false)}
                  className="p-1.5 rounded text-foreground-secondary hover:text-foreground hover:bg-background-hover transition-colors duration-150"
                  title="Close (Esc)"
                >
                  <Minimize2 className="h-4 w-4" />
                </button>
              </div>
            </div>
            {/* Code area */}
            <div className="flex-1 min-h-0 rounded-md border border-border-muted overflow-hidden">
              {renderHighlighter()}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
