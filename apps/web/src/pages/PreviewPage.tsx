import { BlockRenderer } from '@/components/shell/BlockRenderer';
import { FormsProvider } from '@/lib/forms/FormsContext';
import type { Block } from '@/lib/types/blocks';

// 세션 5 Generative UI 카탈로그.
const SAMPLE_BLOCKS: Block[] = [
  {
    type: 'message',
    id: 'preview-msg-1',
    text: '비 오는 날이라 따뜻한 국물 위주로 3곳 추천드려요 🍲',
  },
  {
    type: 'tool_status',
    tool: 'get_weather',
    state: 'done',
  },
  {
    type: 'tool_status',
    tool: 'search_restaurants',
    state: 'done',
  },
  {
    type: 'context_summary',
    applied: ['비 오는 날', '국물 선호', '도보 10분 이내', '1만원 이하'],
  },
  {
    type: 'recommendation_card',
    rank: 1,
    restaurant: {
      id: 'r1',
      name: '종로 설렁탕',
      category: '한식',
      walk_minutes: 5,
      budget_label: '₩9,000',
      estimated_meal_minutes: 25,
    },
    reason:
      '비 오는 날 따뜻한 국물 선호가 기억되어 있고, 회의 전까지 여유 있게 다녀오실 수 있어요.',
    evidence: [
      { label: '날씨', text: '현재 비 · 12°C', source_type: 'live-context' },
      { label: '선호', text: '민지님 국물 요리 선호', source_type: 'memory' },
      { label: '리뷰', text: '"국물이 진하고 양이 많아요"', source_type: 'review' },
    ],
  },
  {
    type: 'badge_row',
    badges: [
      { label: '매콤함 2/5', tone: 'warn' },
      { label: '대기 짧음', tone: 'brand' },
      { label: '1인석 OK', tone: 'info' },
    ],
  },
  {
    type: 'map_pin',
    name: '종로 설렁탕',
    address: '서울 종로구 종로5길 3',
    walk_minutes: 5,
    distance_m: 320,
  },
  {
    type: 'recommendation_card',
    rank: 2,
    restaurant: {
      id: 'r2',
      name: '광화문 순두부',
      category: '한식',
      walk_minutes: 7,
      budget_label: '₩8,500',
      estimated_meal_minutes: 20,
    },
    reason: '순두부도 따뜻한 국물 옵션이면서, 가격이 조금 더 저렴해요.',
    evidence: [
      { label: '메뉴', text: '얼큰순두부 · 해물순두부', source_type: 'menu' },
      { label: '리뷰', text: '"매콤하고 김이 올라와요"', source_type: 'review' },
    ],
  },
  {
    type: 'comparison_table',
    candidates: ['종로 설렁탕', '광화문 순두부'],
    axes: [
      { label: '도보', values: ['5분', '7분'], best: 0 },
      { label: '가격', values: ['₩9,000', '₩8,500'], best: 1 },
      { label: '식사 시간', values: ['25분', '20분'], best: 1 },
    ],
  },
  {
    type: 'link_card',
    url: 'https://example.com',
    title: '종로 설렁탕 — 네이버 지도',
    description: '영업시간·메뉴·위치를 지도에서 바로 확인',
    source: '네이버 지도',
  },
  {
    type: 'quick_actions',
    actions: [
      { key: 'closer', label: '더 가까운 곳', patch: { max_walk_minutes: 5 } },
      { key: 'cheaper', label: '더 저렴한 곳', patch: { budget_max: 8000 } },
      { key: 'spicy', label: '매콤한 거로', patch: {} },
      { key: 'retry', label: '다시 추천', patch: {} },
    ],
  },
  {
    type: 'alert_card',
    severity: 'warning',
    title: '사용자 요구사항 위반 감지',
    summary: '2건의 위반이 있습니다. 재검색을 권장합니다.',
    items: [
      {
        requirement: '1만원 이하',
        card: '스시진',
        reason: '13,000원으로 예산 초과',
      },
      {
        requirement: '해산물 제외',
        card: '스시진',
        reason: '초밥 전문 — 해산물 주메뉴',
      },
    ],
  },
  {
    type: 'choice_chips',
    prompt: '오늘 기분은 어때요?',
    name: 'mood',
    options: [
      { label: '가볍게', value: 'light' },
      { label: '든든하게', value: 'hearty' },
      { label: '매콤하게', value: 'spicy' },
      { label: '깔끔하게', value: 'clean' },
    ],
  },
  { type: 'divider', label: '조건을 한 번에 묶어 물어볼 때는' },
  {
    type: 'message',
    id: 'preview-form-msg',
    text: '조건 몇 가지만 알려주세요 🙂',
  },
  {
    type: 'number_input',
    form_id: 'preview-form-1',
    name: 'budget_max',
    label: '1인 예산',
    placeholder: '예: 10000',
    min: 5000,
    max: 30000,
    unit: '원',
    helper_text: '비워두면 제한 없음',
  },
  {
    type: 'select_input',
    form_id: 'preview-form-1',
    name: 'max_walk_minutes',
    label: '이동시간',
    placeholder: '선택',
    options: [
      { label: '5분 이내', value: '5' },
      { label: '10분 이내', value: '10' },
      { label: '15분 이내', value: '15' },
    ],
  },
  {
    type: 'chips_input',
    form_id: 'preview-form-1',
    name: 'mood_concepts',
    label: '오늘 기분 (복수 선택 가능)',
    multiple: true,
    options: [
      { label: '가볍게', value: 'light' },
      { label: '든든하게', value: 'hearty' },
      { label: '매콤하게', value: 'spicy' },
      { label: '깔끔하게', value: 'clean' },
    ],
  },
  {
    type: 'text_input',
    form_id: 'preview-form-1',
    name: 'free_note',
    label: '자유 메모',
    placeholder: '더 알려주고 싶은 게 있다면…',
  },
  {
    type: 'submit_button',
    form_id: 'preview-form-1',
    label: '추천받기',
  },
  { type: 'divider' },
];

export function PreviewPage() {
  return (
    <div className="preview">
      <header className="preview__header">
        <h1>Generative UI 프리뷰</h1>
        <p>
          세션 5 Generative UI 에서 에이전트가 상황에 따라 아래 block 들을 조합해 응답합니다.
          실제 에이전트 없이 카탈로그를 한눈에 확인하는 화면입니다 — LLM 이 어떤 재료들을
          가지고 UI 를 조립하는지 먼저 감을 잡고 가세요.
        </p>
      </header>

      <FormsProvider
        onSubmit={(formId, values) =>
          alert(`[preview] ${formId} submitted\n${JSON.stringify(values, null, 2)}`)
        }
      >
        {SAMPLE_BLOCKS.map((block, i) => (
          <section key={i} className="preview__block">
            <div className="preview__label">
              <code>{block.type}</code>
            </div>
            <BlockRenderer
              block={block}
              onQuickAction={(a) => alert(`quick_action: ${a.label}`)}
            />
          </section>
        ))}
      </FormsProvider>
    </div>
  );
}
