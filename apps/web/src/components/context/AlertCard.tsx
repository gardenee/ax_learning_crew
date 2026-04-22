import type { AlertCardBlock } from '@/lib/types/blocks';

const TONE_BY_SEVERITY: Record<AlertCardBlock['severity'], string> = {
  success: 'alert--success',
  warning: 'alert--warn',
  error: 'alert--error',
  info: 'alert--info',
};

const ICON_BY_SEVERITY: Record<AlertCardBlock['severity'], string> = {
  success: '✓',
  warning: '⚠',
  error: '✖',
  info: 'ℹ',
};

export function AlertCard({ severity, title, summary, items }: AlertCardBlock) {
  return (
    <div className={`alert ${TONE_BY_SEVERITY[severity]}`}>
      <div className="alert__head">
        <span className="alert__icon" aria-hidden>
          {ICON_BY_SEVERITY[severity]}
        </span>
        <div className="alert__title">{title}</div>
      </div>
      {summary && <p className="alert__summary">{summary}</p>}
      {items.length > 0 && (
        <ul className="alert__items">
          {items.map((it, i) => (
            <li key={i}>
              <strong>{it.card}</strong>
              <span className="alert__req">"{it.requirement}"</span>
              <span className="alert__reason">{it.reason}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
