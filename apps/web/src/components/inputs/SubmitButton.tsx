import { useFormSubmit } from '@/lib/forms/FormsContext';
import type { SubmitButtonBlock } from '@/lib/types/blocks';

export function SubmitButton(props: SubmitButtonBlock) {
  const { submit, submitted } = useFormSubmit(props.form_id);

  return (
    <button
      type="button"
      className="input-submit"
      onClick={submit}
      disabled={submitted}
    >
      {submitted ? '제출 완료' : props.label}
    </button>
  );
}
