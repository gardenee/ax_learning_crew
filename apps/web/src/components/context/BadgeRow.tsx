import type { BadgeRowBlock } from '@/lib/types/blocks';

export function BadgeRow({ badges }: BadgeRowBlock) {
  return (
    <div className="badge-row">
      {badges.map((b, i) => (
        <span key={`${b.label}-${i}`} className={`badge badge--${b.tone ?? 'neutral'}`}>
          {b.label}
        </span>
      ))}
    </div>
  );
}
