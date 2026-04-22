import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';

// LLM 이 message/input_block 들을 자유롭게 섞어 "폼" 을 조립할 수 있도록
// form_id 로 묶인 input 들의 값을 공유하는 context.

type FormState = {
  values: Record<string, unknown>;
  submitted: boolean;
};

type FormsContextValue = {
  getValue: (formId: string, name: string) => unknown;
  setValue: (formId: string, name: string, value: unknown) => void;
  isSubmitted: (formId: string) => boolean;
  submit: (formId: string) => void;
};

const FormsContext = createContext<FormsContextValue | null>(null);

type Props = {
  children: ReactNode;
  onSubmit?: (formId: string, values: Record<string, unknown>) => void;
  // 동일 form_id 로 이미 제출된 적이 있는지 미리 알려주고 싶을 때 (대화 이력 복원용).
  initialSubmittedFormIds?: string[];
};

export function FormsProvider({ children, onSubmit, initialSubmittedFormIds }: Props) {
  const initialState = useMemo<Record<string, FormState>>(() => {
    const init: Record<string, FormState> = {};
    for (const id of initialSubmittedFormIds ?? []) {
      init[id] = { values: {}, submitted: true };
    }
    return init;
  }, [initialSubmittedFormIds]);

  const [forms, setForms] = useState<Record<string, FormState>>(initialState);

  // 최신 values 를 submit 시점에 읽기 위한 ref
  const formsRef = useRef(forms);
  formsRef.current = forms;

  const ensure = (formId: string): FormState =>
    formsRef.current[formId] ?? { values: {}, submitted: false };

  const getValue = useCallback((formId: string, name: string) => {
    return ensure(formId).values[name];
  }, []);

  const setValue = useCallback((formId: string, name: string, value: unknown) => {
    setForms((prev) => {
      const current = prev[formId] ?? { values: {}, submitted: false };
      if (current.submitted) return prev;
      return {
        ...prev,
        [formId]: {
          ...current,
          values: { ...current.values, [name]: value },
        },
      };
    });
  }, []);

  const isSubmitted = useCallback((formId: string) => {
    return ensure(formId).submitted;
  }, []);

  const submit = useCallback(
    (formId: string) => {
      const current = ensure(formId);
      if (current.submitted) return;
      setForms((prev) => ({
        ...prev,
        [formId]: { ...current, submitted: true },
      }));
      onSubmit?.(formId, current.values);
    },
    [onSubmit],
  );

  const value: FormsContextValue = { getValue, setValue, isSubmitted, submit };

  return <FormsContext.Provider value={value}>{children}</FormsContext.Provider>;
}

export function useFormField<T>(formId: string, name: string, fallback?: T) {
  const ctx = useContext(FormsContext);
  if (!ctx) {
    throw new Error('useFormField must be used inside <FormsProvider>.');
  }
  const raw = ctx.getValue(formId, name);
  const value = (raw ?? fallback) as T | undefined;
  const setValue = (v: T) => ctx.setValue(formId, name, v);
  const disabled = ctx.isSubmitted(formId);
  return { value, setValue, disabled };
}

export function useFormSubmit(formId: string) {
  const ctx = useContext(FormsContext);
  if (!ctx) {
    throw new Error('useFormSubmit must be used inside <FormsProvider>.');
  }
  return {
    submit: () => ctx.submit(formId),
    submitted: ctx.isSubmitted(formId),
  };
}
