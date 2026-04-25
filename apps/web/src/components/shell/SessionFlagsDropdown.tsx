import { useEffect, useRef, useState } from 'react';
import { IconSettings } from './icons';
import { FLAG_SPECS, type SessionFlags } from '@/lib/session-flags';

type Props = {
  flags: SessionFlags;
  onToggle: (key: keyof SessionFlags) => void;
};

export function SessionFlagsDropdown({ flags, onToggle }: Props) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const renderChip = (spec: (typeof FLAG_SPECS)[number]) => {
    const active = flags[spec.key];
    return (
      <button
        key={spec.key}
        type="button"
        role="menuitemcheckbox"
        aria-checked={active}
        className={`flags__chip ${active ? 'is-active' : ''}`}
        onClick={() => onToggle(spec.key)}
        title={spec.hint}
      >
        <span className="flags__dot" />
        {spec.label}
      </button>
    );
  };

  return (
    <div className="flags" ref={wrapRef}>
      <button
        type="button"
        className={`flags__btn ${open ? 'is-open' : ''}`}
        onClick={() => setOpen((v) => !v)}
        aria-label="세션 토글"
        aria-haspopup="true"
        aria-expanded={open}
      >
        <IconSettings />
      </button>

      {open && (
        <div className="flags__menu" role="menu">
          <div className="flags__head">Tool</div>
          <div className="flags__chips">{FLAG_SPECS.map(renderChip)}</div>

          <div className="flags__hint">
            {FLAG_SPECS.map((spec) => (
              <div key={spec.key}>
                <b>{spec.label}</b> — {spec.hint}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
