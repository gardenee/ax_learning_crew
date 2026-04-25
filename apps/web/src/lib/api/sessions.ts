import type { Block } from '@/lib/types/blocks';
import { fetchJson } from './http';

export type ChatSessionSummary = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type SessionTurnPayload =
  | { kind: 'user'; text: string }
  | { kind: 'assistant'; blocks: Block[] };

export type SessionDetail = {
  session_id: string;
  turns: SessionTurnPayload[];
};

export async function listSessions(limit = 30): Promise<ChatSessionSummary[]> {
  const data = await fetchJson<{ sessions: ChatSessionSummary[] }>(
    `/api/agent/sessions?limit=${limit}`,
  );
  return data.sessions ?? [];
}

export async function getSessionDetail(id: string): Promise<SessionDetail> {
  return fetchJson<SessionDetail>(`/api/agent/sessions/${encodeURIComponent(id)}`);
}
