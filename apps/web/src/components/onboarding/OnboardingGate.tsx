// 첫 기동 시 사용자 이름을 받는 게이트.
import { FormEvent, ReactNode, useEffect, useState } from 'react';
import { LogoMark } from '@/components/shell/icons';
import { createMe, getMe, UserMe } from '@/lib/api/users';

type Phase = 'loading' | 'ready' | 'onboarding';

export function OnboardingGate({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<Phase>('loading');
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    getMe()
      .then(me => setPhase(me ? 'ready' : 'onboarding'))
      .catch(err => setLoadError(String(err)));
  }, []);

  if (loadError) {
    return (
      <div className="onboard">
        <div className="onboard__card">
          <h1 className="onboard__title">서버 연결 실패</h1>
          <p className="onboard__sub">{loadError}</p>
        </div>
      </div>
    );
  }

  if (phase === 'loading') return null;

  if (phase === 'onboarding') {
    return <OnboardingModal onDone={() => setPhase('ready')} />;
  }

  return <>{children}</>;
}

function OnboardingModal({ onDone }: { onDone: (me: UserMe) => void }) {
  const [name, setName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmed = name.trim();
  const canSubmit = trimmed.length > 0 && !submitting;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const me = await createMe(trimmed);
      onDone(me);
    } catch (err) {
      setError(String(err));
      setSubmitting(false);
    }
  };

  return (
    <div className="onboard">
      <form className="onboard__card" onSubmit={submit}>
        <div className="onboard__logo" aria-hidden="true">
          <LogoMark size={56} />
        </div>
        <p className="onboard__sub">사용자님, 뭐라고 불러드릴까요?</p>
        <input
          autoFocus
          className="onboard__input"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="이름"
          maxLength={40}
          disabled={submitting}
        />
        <button type="submit" className="onboard__btn" disabled={!canSubmit}>
          {submitting ? '시작하는 중…' : '시작하기'}
        </button>
        {error && <div className="onboard__err">{error}</div>}
      </form>
    </div>
  );
}
