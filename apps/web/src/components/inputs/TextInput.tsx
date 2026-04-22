import { useFormField } from '@/lib/forms/FormsContext';
import type { TextInputBlock } from '@/lib/types/blocks';

export function TextInput(props: TextInputBlock) {
  const { value, setValue, disabled } = useFormField<string>(
    props.form_id,
    props.name,
    props.default_value ?? '',
  );

  return (
    <div className="input-field">
      {props.label && <label className="input-field__label">{props.label}</label>}
      <input
        type="text"
        className="input-field__control"
        value={value ?? ''}
        placeholder={props.placeholder}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
      />
      {props.helper_text && <small className="input-field__helper">{props.helper_text}</small>}
    </div>
  );
}
