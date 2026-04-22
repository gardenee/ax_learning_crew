import React from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import type { MessageBlock } from '@/lib/types/blocks';

// react-markdown이 특수문자/한글과 ** 가 붙은 경우를 놓칠 때를 위한 fallback.
function boldifyString(s: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  const regex = /\*\*([^*\n]+?)\*\*/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(s)) !== null) {
    if (match.index > lastIndex) parts.push(s.slice(lastIndex, match.index));
    parts.push(<strong key={`b-${match.index}`}>{match[1]}</strong>);
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < s.length) parts.push(s.slice(lastIndex));
  return parts.length > 1 ? <>{parts}</> : s;
}

function walkChildren(children: React.ReactNode): React.ReactNode {
  return React.Children.map(children, (child) =>
    typeof child === 'string' ? boldifyString(child) : child,
  );
}

const components: Components = {
  p: ({ children }) => <p>{walkChildren(children)}</p>,
  li: ({ children }) => <li>{walkChildren(children)}</li>,
  strong: ({ children }) => <strong>{walkChildren(children)}</strong>,
  em: ({ children }) => <em>{walkChildren(children)}</em>,
};

export const markdownComponents = components;

export function AssistantMessage({ text, streaming }: MessageBlock) {
  if (!streaming && !text.trim()) return null;
  return (
    <div className="bubble bubble--bot">
      <ReactMarkdown components={components}>{text}</ReactMarkdown>
      {streaming && <span className="cursor" aria-hidden />}
    </div>
  );
}
