import { useEffect, useState } from 'react';

export type SessionFlags = {
  /** 이번 요청에 이전 대화 이력을 LLM 에게 보낼지 */
  remember_history: boolean;
  /** 최종 카드 직전에 evaluate_response 로 evaluation을 할지 (세션 6) */
  self_check: boolean;
  /** Generative UI: 응답을 JSONL block 으로 받을지. OFF 면 LLM 이 block 을 흉내내도 server 가 plain text 로만 회수 (세션 5) */
  gen_ui: boolean;
  /** get_user_memory / update_user_memory (세션 2) */
  tool_memory: boolean;
  /** search_menus / search_restaurants (세션 3) */
  tool_search: boolean;
  /** get_weather (세션 4) */
  tool_weather: boolean;
  /** get_landmark (세션 4) */
  tool_landmark: boolean;
  /** estimate_travel_time (세션 4) */
  tool_travel: boolean;
  /** ask_user — form 요청 (세션 5) */
  tool_ask_user: boolean;
};

// 크루원 스타터 기본값: tool 은 전부 OFF.
// 세션을 진행하면서 가이드가 시키는 대로 하나씩 ON 으로 토글한다.
// `remember_history` 는 같은 대화에서 이전 발화를 LLM 이 보는 자연스러운 기본 동작이라 ON 유지.
// `gen_ui` 는 세션 5 부터 ON — 그 전엔 LLM 이 JSONL block 을 흉내내도 server 가 plain text 로 회수.
export const DEFAULT_FLAGS: SessionFlags = {
  remember_history: true,
  self_check: false,
  gen_ui: false,
  tool_memory: false,
  tool_search: false,
  tool_weather: false,
  tool_landmark: false,
  tool_travel: false,
  tool_ask_user: false,
};

export type FlagSpec = {
  key: keyof SessionFlags;
  label: string;
  hint: string;
};

// 학습 순서대로 — 세션 1 (대화 이력) → 세션 2~6 (기능 누적).
export const FLAG_SPECS: FlagSpec[] = [
  {
    key: 'remember_history',
    label: '이 대화 기억하기',
    hint: '이전 대화 이력을 함께 전송 · 기록',
  },
  {
    key: 'tool_memory',
    label: '메모리',
    hint: '사용자 선호 조회 / 기록',
  },
  {
    key: 'tool_search',
    label: '식당 지식기반',
    hint: '메뉴 · 식당 벡터 검색',
  },
  {
    key: 'tool_weather',
    label: '날씨',
    hint: '실시간 날씨',
  },
  {
    key: 'tool_landmark',
    label: '기준 장소 좌표',
    hint: '역 · 건물 이름 → 좌표',
  },
  {
    key: 'tool_travel',
    label: '이동시간',
    hint: '도보 이동시간 추정',
  },
  {
    key: 'gen_ui',
    label: 'Generative UI',
    hint: '응답을 JSONL block 으로 (끄면 plain text). 켜면 폼으로 되묻기도 함께 활성화',
  },
  {
    key: 'self_check',
    label: '응답 평가',
    hint: '응답 직전 자기 평가 (요구 위반 · 환각 차단)',
  },
];

const STORAGE_KEY = 'menu-agent:session-flags';

function readFromStorage(): SessionFlags {
  if (typeof window === 'undefined') return { ...DEFAULT_FLAGS };
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_FLAGS };
    const parsed = JSON.parse(raw) as Partial<SessionFlags>;
    return { ...DEFAULT_FLAGS, ...parsed };
  } catch {
    return { ...DEFAULT_FLAGS };
  }
}

function writeToStorage(flags: SessionFlags) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(flags));
  } catch {
    // storage 접근 실패는 무시
  }
}

export function useSessionFlags() {
  const [flags, setFlags] = useState<SessionFlags>(readFromStorage);

  useEffect(() => {
    writeToStorage(flags);
  }, [flags]);

  const toggle = (key: keyof SessionFlags) => {
    setFlags((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return { flags, toggle };
}
