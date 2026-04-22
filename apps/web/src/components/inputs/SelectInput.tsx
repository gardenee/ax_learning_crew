import { useFormField } from '@/lib/forms/FormsContext';
import type { SelectInputBlock } from '@/lib/types/blocks';

export function SelectInput(props: SelectInputBlock) {
  const { value, setValue, disabled } = useFormField<string>(
    props.form_id,
    props.name,
    props.default_value ?? '',
  );

  return (
    <div className="input-field">
      {props.label && <label className="input-field__label">{props.label}</label>}
      <select
        className="input-field__control input-field__control--select"
        value={value ?? ''}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
      >
        <option value="" disabled>
          {props.placeholder ?? '선택하세요'}
        </option>
        {props.options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {props.helper_text && <small className="input-field__helper">{props.helper_text}</small>}
    </div>
  );
}
