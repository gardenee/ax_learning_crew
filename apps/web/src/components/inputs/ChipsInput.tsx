import { useFormField } from '@/lib/forms/FormsContext';
import type { ChipsInputBlock } from '@/lib/types/blocks';

export function ChipsInput(props: ChipsInputBlock) {
  const multiple = props.multiple ?? false;
  const fallback = multiple
    ? (Array.isArray(props.default_value) ? props.default_value : [])
    : (typeof props.default_value === 'string' ? props.default_value : '');
  const { value, setValue, disabled } = useFormField<string | string[]>(
    props.form_id,
    props.name,
    fallback,
  );

  const isOn = (v: string) => {
    if (multiple) return Array.isArray(value) && value.includes(v);
    return value === v;
  };

  const toggle = (v: string) => {
    if (disabled) return;
    if (multiple) {
      const arr = Array.isArray(value) ? value : [];
      setValue(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);
    } else {
      setValue(value === v ? '' : v);
    }
  };

  return (
    <div className="input-field">
      {props.label && <label className="input-field__label">{props.label}</label>}
      <div className="input-field__chips">
        {props.options.map((opt) => (
          <button
            type="button"
            key={opt.value}
            className={`chip ${isOn(opt.value) ? 'chip--on' : ''}`}
            disabled={disabled}
            onClick={() => toggle(opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>
      {props.helper_text && <small className="input-field__helper">{props.helper_text}</small>}
    </div>
  );
}
