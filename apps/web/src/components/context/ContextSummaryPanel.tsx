import type { ContextSummaryBlock } from '@/lib/types/blocks';

export function ContextSummaryPanel({ applied }: ContextSummaryBlock) {
  return (
    <div className="ctx">
      <div className="ctx__lbl">적용된 조건</div>
      <div className="ctx__chips">
        {applied.map((item, i) => (
          <span key={i} className="ctx__chip">
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
