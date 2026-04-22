import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import type { ReasoningBlock as ReasoningBlockType } from '@/lib/types/blocks';
import { IconChevron } from '../shell/icons';
import { markdownComponents } from './AssistantMessage';

export function ReasoningBlock({ text, streaming, collapsed }: ReasoningBlockType) {
  const [open, setOpen] = useState(!collapsed);

  useEffect(() => {
    if (collapsed) setOpen(false);
  }, [collapsed]);

  return (
    <div className={`reasoning${open ? ' reasoning--open' : ''}`}>
      <button
        type="button"
        className="reasoning__head"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="reasoning__ic" aria-hidden>
          <IconChevron />
        </span>
        <span className="reasoning__label">thinking</span>
        {streaming && <span className="reasoning__dot" aria-hidden />}
      </button>
      {open && (
        <div className="reasoning__body">
          <ReactMarkdown components={markdownComponents}>{text}</ReactMarkdown>
          {streaming && <span className="cursor" aria-hidden />}
        </div>
      )}
    </div>
  );
}
