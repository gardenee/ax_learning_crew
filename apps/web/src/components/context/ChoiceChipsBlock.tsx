import type { ChoiceChipsBlock, ChoiceChipOption, QuickAction } from '@/lib/types/blocks';

type Props = ChoiceChipsBlock & {
  onAction: (action: QuickAction) => void;
  disabled?: boolean;
};

export function ChoiceChipsBlockView({ prompt, options, name, onAction, disabled }: Props) {
  const key = name ?? 'choice';
  return (
    <div className="choice-chips">
      {prompt && <div className="choice-chips__prompt">{prompt}</div>}
      <div className="choice-chips__row">
        {options.map((opt: ChoiceChipOption) => (
          <button
            key={opt.value}
            className="choice-chips__chip"
            onClick={() => onAction({ key: opt.value, label: opt.label, patch: { [key]: opt.value } })}
            disabled={disabled}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
