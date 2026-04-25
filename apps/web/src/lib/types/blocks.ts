// 에이전트가 생성하는 block 타입들.

export type MessageBlock = {
  type: 'message';
  id: string;
  text: string;
  streaming?: boolean;
};

export type ToolStatusBlock = {
  type: 'tool_status';
  tool: string;
  state: 'running' | 'done';
  input?: Record<string, unknown>;
  result?: unknown; // tool 실행 결과 — 학습용으로 펼쳐서 보여준다.
  collapsed?: boolean;
};

export type ReasoningBlock = {
  type: 'reasoning';
  id: string;
  text: string;
  streaming?: boolean;
  collapsed?: boolean;
};

export type EvidenceSnippet = {
  label: string;
  text: string;
  source_type: 'menu' | 'review' | 'summary' | 'memory' | 'live-context' | 'situation_hint';
};

export type RestaurantSummary = {
  id: string;
  name: string;
  category: string;
  walk_minutes?: number;
  distance_m?: number;
  budget_label?: string;
  estimated_meal_minutes?: number;
  map_url?: string; // 카카오맵 deep link (백엔드 candidate 에서 자동 생성)
  image_url?: string; // (옵션) thumbnail — 데이터에 있을 때만
};

export type QuickAction = {
  key: string;
  label: string;
  patch: Record<string, unknown>;
};

export type CompareAxis = {
  label: string;
  values: string[];
  best?: number;
};

export type RecommendationCardBlock = {
  type: 'recommendation_card';
  rank: number;
  restaurant: RestaurantSummary;
  reason: string;
  evidence: EvidenceSnippet[];
  dislike_reason_chips?: string[];
};

export type ComparisonTableBlock = {
  type: 'comparison_table';
  candidates: string[];
  axes: CompareAxis[];
};

export type QuickActionsBlock = {
  type: 'quick_actions';
  actions: QuickAction[];
};

export type ChoiceChipOption = {
  label: string;
  value: string;
};

export type ChoiceChipsBlock = {
  type: 'choice_chips';
  prompt: string;
  options: ChoiceChipOption[];
  name?: string;
};

export type ContextSummaryBlock = {
  type: 'context_summary';
  applied: string[];
};

export type InputOption = {
  label: string;
  value: string;
};

type InputBase = {
  form_id: string;
  name: string;
  label?: string;
  helper_text?: string;
  required?: boolean;
};

export type TextInputBlock = InputBase & {
  type: 'text_input';
  placeholder?: string;
  default_value?: string;
};

export type NumberInputBlock = InputBase & {
  type: 'number_input';
  placeholder?: string;
  min?: number;
  max?: number;
  unit?: string;
  default_value?: number;
};

export type ChipsInputBlock = InputBase & {
  type: 'chips_input';
  options: InputOption[];
  multiple?: boolean;
  default_value?: string | string[];
};

export type SelectInputBlock = InputBase & {
  type: 'select_input';
  options: InputOption[];
  placeholder?: string;
  default_value?: string;
};

export type SubmitButtonBlock = {
  type: 'submit_button';
  form_id: string;
  label: string;
};

export type DividerBlock = {
  type: 'divider';
  label?: string;
};

export type BadgeTone = 'neutral' | 'brand' | 'warn' | 'info' | 'accent';

export type BadgeRowBlock = {
  type: 'badge_row';
  badges: Array<{ label: string; tone?: BadgeTone }>;
};

export type MapPinBlock = {
  type: 'map_pin';
  name: string;
  address?: string;
  walk_minutes?: number;
  distance_m?: number;
  lat?: number;
  lng?: number;
};

export type LinkCardBlock = {
  type: 'link_card';
  url: string;
  title: string;
  description?: string;
  source?: string;
};

export type AlertItem = {
  requirement: string;
  card: string;
  reason: string;
};

export type AlertCardBlock = {
  type: 'alert_card';
  severity: 'warning' | 'error' | 'info' | 'success';
  title: string;
  summary: string;
  items: AlertItem[];
};

export type Block =
  | MessageBlock
  | ToolStatusBlock
  | ReasoningBlock
  | RecommendationCardBlock
  | ComparisonTableBlock
  | QuickActionsBlock
  | ChoiceChipsBlock
  | ContextSummaryBlock
  | TextInputBlock
  | NumberInputBlock
  | ChipsInputBlock
  | SelectInputBlock
  | SubmitButtonBlock
  | DividerBlock
  | BadgeRowBlock
  | MapPinBlock
  | LinkCardBlock
  | AlertCardBlock;
