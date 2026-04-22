type IconProps = { size?: number };

export function IconSend({ size = 18 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 2L11 13" />
      <path d="M22 2l-7 20-4-9-9-4z" />
    </svg>
  );
}

export function IconStop({ size = 18 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor">
      <rect x="5" y="5" width="14" height="14" rx="2.5" />
    </svg>
  );
}

export function IconPlus({ size = 16 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function IconChat({ size = 18 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12a8 8 0 0 1-11.8 7L4 20l1-4.2A8 8 0 1 1 21 12z" />
    </svg>
  );
}

export function IconSparkle({ size = 16 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor">
      <path d="M12 2.5l1.6 4.7L18 9l-4.4 1.8L12 15.5 10.4 10.8 6 9l4.4-1.8z" />
      <path d="M19 14l.9 2.3L22 17l-2.1.7L19 20l-.9-2.3L16 17l2.1-.7z" />
    </svg>
  );
}

export function IconWalk({ size = 14 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="13" cy="4.5" r="1.5" />
      <path d="M8.5 22l2-6 2 2v5" />
      <path d="M15 22l-2-5 1-4" />
      <path d="M10 9l2-2 3 2 2 1" />
    </svg>
  );
}

export function IconClock({ size = 14 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.75">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" strokeLinecap="round" />
    </svg>
  );
}

export function IconWon({ size = 14 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 7l3 11 3-8 2 8 3-11" />
      <path d="M15 7l3 11" />
      <path d="M3 12h18" />
    </svg>
  );
}

export function IconChevron({ size = 14 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

export function IconArrowDown({ size = 18 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14M6 13l6 6 6-6" />
    </svg>
  );
}

export function IconCheck({ size = 12 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 12l5 5L20 6" />
    </svg>
  );
}

export function IconThumbsUp({ size = 15 }: IconProps) {
  return (
    <svg viewBox="-1 -1 26 26" width={size} height={size} overflow="visible" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 10v12" />
      <path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H7V10a4 4 0 0 0 4-4V2" />
    </svg>
  );
}

export function IconThumbsDown({ size = 15 }: IconProps) {
  return (
    <svg viewBox="-1 -1 26 26" width={size} height={size} overflow="visible" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 14V2" />
      <path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H17v12a4 4 0 0 0-4 4v2" />
    </svg>
  );
}

export function IconPin({ size = 14 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

export function IconSettings({ size = 18 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

export function LogoMark({ size = 34 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <defs>
        <linearGradient id="ds-bowl-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8FAE3C" />
          <stop offset="1" stopColor="#6B8F27" />
        </linearGradient>
      </defs>
      <path d="M22 10 C 20 14, 26 16, 24 20" stroke="#33451A" strokeWidth="2.5" strokeLinecap="round" fill="none" opacity=".5" />
      <path d="M32 8  C 30 12, 36 14, 34 18" stroke="#33451A" strokeWidth="2.5" strokeLinecap="round" fill="none" opacity=".65" />
      <path d="M42 10 C 40 14, 46 16, 44 20" stroke="#33451A" strokeWidth="2.5" strokeLinecap="round" fill="none" opacity=".5" />
      <ellipse cx="32" cy="26" rx="24" ry="5" fill="#E6EFC8" />
      <path d="M10 26 C 10 42, 20 54, 32 54 C 44 54, 54 42, 54 26 Z" fill="url(#ds-bowl-grad)" />
      <path d="M14 34 C 20 38, 44 38, 50 34" stroke="#E6EFC8" strokeWidth="2.5" strokeLinecap="round" fill="none" opacity=".85" />
      <circle cx="26" cy="41" r="1.8" fill="#1A1F14" />
      <circle cx="38" cy="41" r="1.8" fill="#1A1F14" />
      <circle cx="22" cy="45" r="1.8" fill="#C6D88A" opacity=".9" />
      <circle cx="42" cy="45" r="1.8" fill="#C6D88A" opacity=".9" />
    </svg>
  );
}
