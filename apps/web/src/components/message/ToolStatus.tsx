import { useState, useEffect } from 'react';
import type { ToolStatusBlock } from '@/lib/types/blocks';
import { IconCheck } from '../shell/icons';

export function ToolStatus({ tool, state, input, result, collapsed }: ToolStatusBlock) {
  const label = state === 'running' ? '사용 중' : '완료';
  const hasArgs = !!input && Object.keys(input).length > 0;
  const hasResult = result !== undefined && result !== null;
  const expandable = hasArgs || hasResult;

  const initialOpen = state === 'running' ? !collapsed : collapsed === false;
  const [open, setOpen] = useState(initialOpen);

  useEffect(() => {
    if (state === 'done' && collapsed) setOpen(false);
    if (state === 'running' && !collapsed) setOpen(true);
  }, [state, collapsed]);

  const toggle = () => setOpen((v) => !v);

  const inner = (
    <>
      <span className="tool__ic" aria-hidden>
        {state === 'done' ? <IconCheck /> : <span className="tool__dot" />}
      </span>
      <code className="tool__name">{tool}</code>
      <span className="tool__lbl">{label}</span>
    </>
  );

  return (
    <div className={`tool tool--${state}${expandable && open ? ' tool--expanded' : ''}`}>
      {expandable ? (
        <button
          type="button"
          className="tool__row tool__row--btn"
          onClick={toggle}
          aria-expanded={open}
        >
          {inner}
        </button>
      ) : (
        <div className="tool__row">{inner}</div>
      )}
      {expandable && open && (
        <div className="tool__detail">
          {hasArgs && (
            <div className="tool__section tool__section--input">
              <div className="tool__section-label">입력</div>
              <pre className="tool__args">{JSON.stringify(input, null, 2)}</pre>
            </div>
          )}
          {hasResult && (
            <div className="tool__section tool__section--result">
              <div className="tool__section-label">결과</div>
              <pre className="tool__args tool__args--result">{prettyJSON(result)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function prettyJSON(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
