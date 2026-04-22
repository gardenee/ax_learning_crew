import type { QuickActionsBlock, QuickAction } from '@/lib/types/blocks';

type Props = QuickActionsBlock & {
  onAction: (action: QuickAction) => void;
  disabled?: boolean;
};

export function QuickActionChips({ actions, onAction, disabled }: Props) {
  return (
    <div className="qa">
      {actions.map((action) => (
        <button
          key={action.key}
          className="qa__chip"
          onClick={() => onAction(action)}
          disabled={disabled}
        >
          {action.label}
        </button>
      ))}
    </div>
  );
}
