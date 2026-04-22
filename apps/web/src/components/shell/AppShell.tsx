import { useEffect, useState, type ReactNode } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { IconChat, IconPlus, LogoMark } from './icons';
import { listSessions, type ChatSessionSummary } from '@/lib/api/sessions';

export const NEW_SESSION_EVENT = 'app:new-session-requested';
export const SESSIONS_CHANGED_EVENT = 'app:sessions-changed';

export function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      try {
        const data = await listSessions();
        if (!cancelled) {
          setSessions(data);
          setLoadError(false);
        }
      } catch {
        if (!cancelled) setLoadError(true);
      }
    };
    refresh();
    const handler = () => refresh();
    window.addEventListener(SESSIONS_CHANGED_EVENT, handler);
    return () => {
      cancelled = true;
      window.removeEventListener(SESSIONS_CHANGED_EVENT, handler);
    };
  }, []);

  const handleNewSession = () => {
    navigate('/session/new');
    window.dispatchEvent(new CustomEvent(NEW_SESSION_EVENT));
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand" aria-label="홈">
          <LogoMark />
          <div className="brand__name">
            오늘 점심 <b>뭐 먹지</b>?
          </div>
        </NavLink>
        <button className="btn-new" onClick={handleNewSession}>
          <IconPlus /> 새 추천
        </button>

        <div className="nav-label">최근 대화</div>
        <nav className="nav">
          {sessions.length === 0 && (
            <div className="nav-empty">
              {loadError ? '목록을 불러오지 못했어요' : '아직 대화가 없어요'}
            </div>
          )}
          {sessions.map((s) => (
            <NavLink
              key={s.id}
              to={`/session/${s.id}`}
              className={({ isActive }) => `nav-item ${isActive ? 'is-active' : ''}`}
            >
              <IconChat />
              <div className="nav-item__body">
                <div className="nav-item__title">{s.title}</div>
                <div className="nav-item__when">{formatWhen(s.updated_at)}</div>
              </div>
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const now = new Date();
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  if (sameDay) {
    return `오늘 ${d.getHours().toString().padStart(2, '0')}:${d
      .getMinutes()
      .toString()
      .padStart(2, '0')}`;
  }
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const isYesterday =
    d.getFullYear() === yesterday.getFullYear() &&
    d.getMonth() === yesterday.getMonth() &&
    d.getDate() === yesterday.getDate();
  if (isYesterday) return '어제';
  return `${d.getMonth() + 1}/${d.getDate()}`;
}
