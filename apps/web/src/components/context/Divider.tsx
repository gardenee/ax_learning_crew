import type { DividerBlock } from '@/lib/types/blocks';

export function Divider({ label }: DividerBlock) {
  if (!label) return <div className="divider" role="separator" />;
  return (
    <div className="divider divider--labeled" role="separator">
      <span className="divider__label">{label}</span>
    </div>
  );
}
