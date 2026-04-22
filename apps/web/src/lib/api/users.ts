// 사용자 onboarding 전용 API.
import { fetchJson } from './http';

export type UserMe = {
  id: string;
  handle: string;
  display_name: string;
  default_location_alias: string | null;
};

/** 404 면 null 을 반환한다 (onboarding 필요 신호). */
export async function getMe(): Promise<UserMe | null> {
  const res = await fetch('/api/users/me', { headers: { Accept: 'application/json' } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`/api/users/me failed: ${res.status}`);
  return (await res.json()) as UserMe;
}

export async function createMe(displayName: string): Promise<UserMe> {
  return fetchJson<UserMe>('/api/users/me', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ display_name: displayName }),
  });
}
