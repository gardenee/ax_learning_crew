// POST /api/feedback — 세션 6 에서 완성된 reflection 경로.
// 버튼 클릭이 feedback_events 로그 + preference_signals 상태에 반영되고,
// 다음 턴의 get_user_memory 가 자동으로 읽어 추천에 녹인다.
//
// 저장 규칙:
//   - liked              → events append + signals upsert
//   - disliked (reason X) → events append + signals upsert (식당 블랙리스트)
//   - disliked (reason O) → events append 만. signals 는 건드리지 않음 —
//                           "이유 있는 거부" 는 다음 턴 get_user_memory 가
//                           최근 dislike 로그를 읽어 LLM 이 해석.
//   - visited            → events append 만 (방문 사실, 선호 아님)
//   - clear=true         → events 는 그대로 두고 signals 만 삭제 (토글 off)
import { CURRENT_USER_ID } from '@/lib/config';
import { fetchJson } from './http';

export type FeedbackVerdict = 'liked' | 'disliked' | 'visited';

export async function submitFeedback(args: {
  sessionId: string | null;
  restaurantId: string;
  restaurantName?: string | null;
  verdict: FeedbackVerdict;
  reasonTags?: string[];
  freeText?: string | null;
  clear?: boolean;
}) {
  return fetchJson<unknown>('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: args.sessionId,
      user_id: CURRENT_USER_ID,
      candidate_restaurant_id: args.restaurantId,
      candidate_restaurant_name: args.restaurantName ?? null,
      verdict: args.verdict,
      reason_tags: args.reasonTags ?? [],
      free_text: args.freeText ?? null,
      clear: args.clear ?? false,
    }),
  });
}
