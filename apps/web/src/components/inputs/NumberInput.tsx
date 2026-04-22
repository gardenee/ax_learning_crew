import { useFormField } from '@/lib/forms/FormsContext';
import type { NumberInputBlock } from '@/lib/types/blocks';

export function NumberInput(props: NumberInputBlock) {
  const { value, setValue, disabled } = useFormField<number | undefined>(
    props.form_id,
    props.name,
    props.default_value,
  );

  return (
    <div className="input-field">
      {props.label && <label className="input-field__label">{props.label}</label>}
      <div className="input-field__wrap">
        <input
          type="number"
          className="input-field__control"
          value={value ?? ''}
          placeholder={props.placeholder}
          min={props.min}
          max={props.max}
          disabled={disabled}
          onChange={(e) => {
            const raw = e.target.value;
            setValue(raw === '' ? undefined : Number(raw));
          }}
        />
        {props.unit && <span className="input-field__unit">{props.unit}</span>}
      </div>
      {props.helper_text && <small className="input-field__helper">{props.helper_text}</small>}
    </div>
  );
}
