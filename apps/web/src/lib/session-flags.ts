import { useEffect, useState } from 'react';

export type SessionFlags = {
  /** 이번 요청에 이전 대화 이력을 LLM 에게 보낼지 */
  remember_history: boolean;
  /** 최종 카드 직전에 evaluate_response 로 evaluation을 할지 */
  self_check: boolean;
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

export const DEFAULT_FLAGS: SessionFlags = {
  remember_history: true,
  self_check: true,
  tool_memory: true,
  tool_search: true,
  tool_weather: true,
  tool_landmark: true,
  tool_travel: true,
  tool_ask_user: true,
};

export type FlagSpec = {
  key: keyof SessionFlags;
  label: string;
  hint: string;
  group?: 'behavior' | 'tool';
};

export const FLAG_SPECS: FlagSpec[] = [
  {
    key: 'remember_history',
    label: '이 대화 기억하기',
    hint: '켜면 이전 대화 이력을 함께 보내고, 이번 대화도 기록으로 저장합니다.',
    group: 'behavior',
  },
  {
    key: 'self_check',
    label: '응답 평가',
    hint: '켜면 최종 카드 직전에 자기 평가를 돌려 사용자 요구 위반을 잡아냅니다.',
    group: 'behavior',
  },
  {
    key: 'tool_memory',
    label: '메모리',
    hint: '사용자 선호 조회/기록 tool. 끄면 개인화 없이 범용 추천만 돌아갑니다.',
    group: 'tool',
  },
  {
    key: 'tool_search',
    label: '검색 (RAG)',
    hint: '메뉴/식당 검색 tool. 끄면 에이전트가 DB 의 식당을 전혀 추천할 수 없습니다.',
    group: 'tool',
  },
  {
    key: 'tool_weather',
    label: '날씨',
    hint: '실시간 날씨 tool. 끄면 날씨 기반 추천이 불가합니다.',
    group: 'tool',
  },
  {
    key: 'tool_landmark',
    label: '랜드마크',
    hint: '랜드마크/역 → 좌표 tool. 끄면 위치 기반 필터링이 어려워집니다.',
    group: 'tool',
  },
  {
    key: 'tool_travel',
    label: '이동시간',
    hint: '도보 이동시간 추정 tool. 끄면 후보별 walk_minutes 표기가 사라집니다.',
    group: 'tool',
  },
  {
    key: 'tool_ask_user',
    label: '추가 질문 폼',
    hint: '사용자에게 form 으로 되묻는 ask_user tool. 끄면 에이전트가 자연어로만 되묻습니다.',
    group: 'tool',
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
