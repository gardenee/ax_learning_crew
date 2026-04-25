import type { Block } from './blocks';

export type AgentRunRequest = {
  session_id?: string | null;
  participant_ids?: string[];
  constraints?: {
    budget_max?: number;
    max_walk_minutes?: number;
    max_meal_minutes?: number;
  };
  user_message?: string;
  form_answers?: Record<string, unknown>;
  constraint_patch?: Record<string, unknown>;
  session_flags?: {
    remember_history?: boolean;
    self_check?: boolean;
    tool_memory?: boolean;
    tool_search?: boolean;
    tool_weather?: boolean;
    tool_landmark?: boolean;
    tool_travel?: boolean;
    tool_ask_user?: boolean;
  };
};

export type DebugInfo = {
  tool_calls: string[];
  latency_ms: number;
};

export type AgentEvent =
  | { type: 'session'; session_id: string }
  | { type: 'message_start'; id: string }
  | { type: 'message_delta'; id: string; text: string }
  | { type: 'message_end'; id: string }
  | { type: 'reasoning_start'; id: string }
  | { type: 'reasoning_delta'; id: string; text: string }
  | { type: 'reasoning_end'; id: string }
  | {
      type: 'tool_status';
      tool: string;
      state: 'start' | 'done';
      input?: Record<string, unknown>;
      result?: unknown;
    }
  | { type: 'done'; debug_info: DebugInfo }
  | { type: 'error'; message: string }
  | (Block & { type: Exclude<Block['type'], 'message' | 'tool_status' | 'reasoning'> });
