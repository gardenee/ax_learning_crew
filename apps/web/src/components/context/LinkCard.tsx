import type { LinkCardBlock } from '@/lib/types/blocks';

export function LinkCard({ url, title, description, source }: LinkCardBlock) {
  return (
    <a className="link-card" href={url} target="_blank" rel="noopener noreferrer">
      <div className="link-card__body">
        {source && <div className="link-card__source">{source}</div>}
        <div className="link-card__title">{title}</div>
        {description && <div className="link-card__desc">{description}</div>}
      </div>
      <span className="link-card__arrow" aria-hidden>↗</span>
    </a>
  );
}
