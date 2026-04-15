import { useRef, useCallback } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { cn } from '@/lib/utils';

const editorTheme = {
  ...oneDark,
  'pre[class*="language-"]': {
    ...oneDark['pre[class*="language-"]'],
    background: 'transparent',
    margin: 0,
    padding: '8px 12px',
    fontSize: '13px',
    lineHeight: '1.5',
    overflow: 'auto',
  },
  'code[class*="language-"]': {
    ...oneDark['code[class*="language-"]'],
    background: 'transparent',
    fontSize: '13px',
    lineHeight: '1.5',
  },
};

interface PythonCodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function PythonCodeEditor({ value, onChange, placeholder, disabled, className }: PythonCodeEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const preRef = useRef<HTMLDivElement>(null);

  const handleScroll = useCallback(() => {
    if (textareaRef.current && preRef.current) {
      preRef.current.scrollTop = textareaRef.current.scrollTop;
      preRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Tab') {
        e.preventDefault();
        const ta = e.currentTarget;
        const start = ta.selectionStart;
        const end = ta.selectionEnd;
        const updated = value.substring(0, start) + '    ' + value.substring(end);
        onChange(updated);
        requestAnimationFrame(() => {
          ta.selectionStart = ta.selectionEnd = start + 4;
        });
      }
    },
    [value, onChange],
  );

  // Ensure the highlight block always has a trailing newline so it
  // doesn't collapse the last empty line the user is typing on.
  const displayCode = value || placeholder || '';

  return (
    <div className={cn('relative rounded border border-border overflow-hidden', className)} style={{ background: '#1c1c28' }}>
      {/* Syntax-highlighted backdrop */}
      <div
        ref={preRef}
        aria-hidden
        className="absolute inset-0 overflow-hidden pointer-events-none"
      >
        <SyntaxHighlighter
          language="python"
          style={editorTheme}
          customStyle={{ minHeight: '100%', whiteSpace: 'pre' }}
        >
          {displayCode + '\n'}
        </SyntaxHighlighter>
      </div>

      {/* Editable textarea (transparent text, visible caret) */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onScroll={handleScroll}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        spellCheck={false}
        autoCorrect="off"
        autoCapitalize="off"
        className={cn(
          'relative w-full font-mono text-[13px] leading-[1.5] bg-transparent text-transparent caret-white',
          'px-3 py-2 resize-y min-h-[140px] outline-none',
          'focus:ring-1 focus:ring-border-focus',
          'disabled:opacity-50',
          !value && 'text-transparent',
        )}
        style={{ WebkitTextFillColor: 'transparent' }}
      />
    </div>
  );
}
