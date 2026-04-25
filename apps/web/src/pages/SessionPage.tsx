import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { streamAgent } from '@/lib/api/agent';
import { BlockRenderer } from '@/components/shell/BlockRenderer';
import { IconArrowDown, IconSend, IconStop } from '@/components/shell/icons';
import { SessionFlagsDropdown } from '@/components/shell/SessionFlagsDropdown';
import {
  NEW_SESSION_EVENT,
  SESSIONS_CHANGED_EVENT,
} from '@/components/shell/AppShell';
import type { Block, QuickAction } from '@/lib/types/blocks';
import type { AgentEvent, AgentRunRequest, DebugInfo } from '@/lib/types/api';
import { CURRENT_USER_ID } from '@/lib/config';
import { getSessionDetail } from '@/lib/api/sessions';
import { useSessionFlags } from '@/lib/session-flags';
import { FormsProvider } from '@/lib/forms/FormsContext';

type UserTurn = { kind: 'user'; id: string; text: string };
type AssistantTurn = {
  kind: 'assistant';
  id: string;
  blocks: Block[];
  // DB 에서 복원된 과거 턴 UI 요소들은 readonly
  readonly?: boolean;
};
type Turn = UserTurn | AssistantTurn;

let turnCounter = 0;
const nextTurnId = (prefix: string) => `${prefix}_${++turnCounter}`;

const EMPTY_SUGGESTIONS: { emoji: string; text: string }[] = [
  { emoji: '🍱', text: '오늘 점심 뭐 먹지?' },
  { emoji: '🌧️', text: '비 와서 뜨끈한 국물 당겨' },
  { emoji: '📍', text: '발산역 근처 혼밥하기 좋은 곳' },
  { emoji: '⏱️', text: '30분 안에 호다닥 먹을 수 있는 곳' },
];

export function SessionPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { id: routeSessionId } = useParams<{ id?: string }>();
  const initialPrompt = (location.state as { prompt?: string } | null)?.prompt;

  const [turns, setTurns] = useState<Turn[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(
    routeSessionId && routeSessionId !== 'new' ? routeSessionId : null,
  );
  const [userMessage, setUserMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState('');
  const [debugInfo, setDebugInfo] = useState<DebugInfo | null>(null);
  const [showScrollFab, setShowScrollFab] = useState(false);
  const { flags, toggle: toggleFlag } = useSessionFlags();
  const transcriptRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const autoSentRef = useRef(false);
  const pinnedRef = useRef(true);
  const abortRef = useRef<AbortController | null>(null);
  const justCreatedIdRef = useRef<string | null>(null);

  // 이번 턴 동안만 유효한 휘발성 상태 초기화
  const clearTransient = () => {
    setError('');
    setDebugInfo(null);
  };

  useEffect(() => {
    if (!pinnedRef.current) return;
    transcriptRef.current?.scrollTo({
      top: transcriptRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [turns]);

  const handleScroll = () => {
    const el = transcriptRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    pinnedRef.current = atBottom;
    setShowScrollFab(!atBottom);
  };

  const scrollToBottom = () => {
    const el = transcriptRef.current;
    if (!el) return;
    pinnedRef.current = true;
    setShowScrollFab(false);
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  };

  // 홈에서 전달된 initialPrompt가 있으면 자동으로 한 번만 전송.
  useEffect(() => {
    if (!initialPrompt || autoSentRef.current) return;
    autoSentRef.current = true;
    callAgent(initialPrompt, { user_message: initialPrompt });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialPrompt]);

  // 사이드바 "새 추천" 버튼 클릭 시 세션 리셋
  useEffect(() => {
    const handler = () => {
      abortRef.current?.abort();
      setTurns([]);
      setSessionId(null);
      setUserMessage('');
      clearTransient();
      autoSentRef.current = false;
      justCreatedIdRef.current = null;
      pinnedRef.current = true;
      setShowScrollFab(false);
      inputRef.current?.focus();
    };
    window.addEventListener(NEW_SESSION_EVENT, handler);
    return () => window.removeEventListener(NEW_SESSION_EVENT, handler);
  }, []);

  // 페이지 이탈 / 컴포넌트 언마운트 시 진행 중인 스트림을 취소한다.
  useEffect(() => () => abortRef.current?.abort(), []);

  // URL의 세션 id가 바뀌면 사이드바 클릭 등 다른 세션으로 전환한 것으로 간주하고 내역을 로드한다.
  useEffect(() => {
    const currentId = routeSessionId && routeSessionId !== 'new' ? routeSessionId : null;

    if (currentId && justCreatedIdRef.current === currentId) {
      justCreatedIdRef.current = null;
      return;
    }
    abortRef.current?.abort();

    clearTransient();
    autoSentRef.current = true; // 기존 세션으로 들어오는 경우 initialPrompt 자동 전송 방지.
    pinnedRef.current = true;
    setShowScrollFab(false);

    if (!currentId) {
      setSessionId(null);
      setTurns([]);
      inputRef.current?.focus();
      return;
    }

    setSessionId(currentId);
    let cancelled = false;
    (async () => {
      try {
        const detail = await getSessionDetail(currentId);
        if (cancelled) return;
        setTurns(
          detail.turns.map((t) =>
            t.kind === 'user'
              ? { kind: 'user', id: nextTurnId('u'), text: t.text }
              : {
                  kind: 'assistant',
                  id: nextTurnId('a'),
                  blocks: t.blocks as Block[],
                  readonly: true,
                },
          ),
        );
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'load error');
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeSessionId]);

  useEffect(() => {
    if (!initialPrompt) inputRef.current?.focus();
  }, [initialPrompt, routeSessionId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = userMessage.trim();
    if (!text || isStreaming) return;
    setUserMessage('');
    await callAgent(text, { user_message: text });
  };

  const handleQuickAction = (action: QuickAction) => {
    if (isStreaming) return;
    callAgent(action.label, { user_message: action.label, constraint_patch: action.patch });
  };

  const handleFormSubmit = (_formId: string, answers: Record<string, unknown>) => {
    if (isStreaming) return;
    callAgent('(폼 제출)', { form_answers: answers });
  };

  const callAgent = async (userLabel: string, extra: Partial<AgentRunRequest>) => {
    clearTransient();
    setIsStreaming(true);
    pinnedRef.current = true;
    setShowScrollFab(false);

    const controller = new AbortController();
    abortRef.current = controller;

    const userTurn: UserTurn = { kind: 'user', id: nextTurnId('u'), text: userLabel };
    const assistantTurn: AssistantTurn = { kind: 'assistant', id: nextTurnId('a'), blocks: [] };
    setTurns((prev) => [...prev, userTurn, assistantTurn]);

    try {
      const request: AgentRunRequest = {
        session_id: sessionId,
        participant_ids: [CURRENT_USER_ID],
        session_flags: flags,
        ...extra,
      };

      for await (const event of streamAgent(request, controller.signal)) {
        applyEvent(event, assistantTurn.id);
      }
    } catch (err) {
      const isAbort =
        (err instanceof DOMException && err.name === 'AbortError') ||
        (err instanceof Error && err.name === 'AbortError');
      if (!isAbort) setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      setTurns((prev) =>
        prev.map((t) =>
          t.kind === 'assistant' && t.id === assistantTurn.id
            ? { ...t, blocks: collapseReasoning(finalizeStreaming(t.blocks)) }
            : t,
        ),
      );
      setIsStreaming(false);
    }
  };

  const handleStop = () => {
    abortRef.current?.abort();
  };

  const applyEvent = (event: AgentEvent, assistantTurnId: string) => {
    switch (event.type) {
      case 'session':
        setSessionId(event.session_id);
        if (routeSessionId === 'new' || !routeSessionId) {
          justCreatedIdRef.current = event.session_id;
          navigate(`/session/${event.session_id}`, { replace: true });
        }
        window.dispatchEvent(new CustomEvent(SESSIONS_CHANGED_EVENT));
        return;
      case 'done':
        setDebugInfo(event.debug_info);
        setTurns((prev) =>
          prev.map((t) =>
            t.kind === 'assistant' && t.id === assistantTurnId
              ? { ...t, blocks: collapseReasoning(t.blocks) }
              : t,
          ),
        );
        return;
      case 'error':
        setError(event.message);
        return;
      default:
        setTurns((prev) =>
          prev.map((t) =>
            t.kind === 'assistant' && t.id === assistantTurnId
              ? { ...t, blocks: reduceBlocks(t.blocks, event) }
              : t,
          ),
        );
    }
  };

  const isEmpty = turns.length === 0;
  const showSuggestions = isEmpty && !isStreaming;

  return (
    <div className={`session${isEmpty ? ' session--empty' : ''}`}>
      <div className="session__header">
        <SessionFlagsDropdown flags={flags} onToggle={toggleFlag} />
      </div>

      <div className="session__scroll" ref={transcriptRef} onScroll={handleScroll}>
        <div className="session__scroll-inner">
        {turns.map((turn, idx) => {
          if (turn.kind === 'user') {
            return (
              <div key={turn.id} className="turn turn--user">
                <div className="bubble bubble--user">{turn.text}</div>
              </div>
            );
          }
          const isLastTurn = idx === turns.length - 1;
          const showThinking =
            isLastTurn && isStreaming && !hasActiveBlock(turn.blocks);
          const isReadonly = turn.readonly === true;
          const submittedFormIds = isReadonly
            ? Array.from(
                new Set(
                  turn.blocks
                    .map((b) => (b as { form_id?: string }).form_id)
                    .filter((id): id is string => typeof id === 'string' && id.length > 0),
                ),
              )
            : undefined;
          return (
            <div key={turn.id} className="turn turn--bot">
              <FormsProvider
                onSubmit={handleFormSubmit}
                initialSubmittedFormIds={submittedFormIds}
              >
                {mergeMapPinsIntoCards(turn.blocks).map((block, i) => (
                  <BlockRenderer
                    key={`${turn.id}-${i}`}
                    block={block}
                    onQuickAction={isReadonly ? undefined : handleQuickAction}
                    sessionId={sessionId}
                    readonly={isReadonly}
                  />
                ))}
              </FormsProvider>
              {showThinking && (
                <div className="thinking">
                  <span />
                  <span />
                  <span /> 잠깐만요, 생각해볼게요…
                </div>
              )}
            </div>
          );
        })}
        </div>
      </div>

      {showScrollFab && !isEmpty && (
        <button
          type="button"
          className="session__scroll-fab"
          onClick={scrollToBottom}
          aria-label="아래로 내리기"
        >
          <IconArrowDown />
        </button>
      )}

      {error && <div className="session__error">{error}</div>}

      <div className="composer">
        {isEmpty && (
          <h1 className="composer__title">
            오늘 점심 <b>뭐 먹지</b>?
          </h1>
        )}
        <form className="composer__bar" onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            type="text"
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            placeholder={isStreaming ? '답변을 작성 중이에요…' : '오늘은 뭐가 땡기세요?'}
            disabled={isStreaming}
            autoFocus
          />
          {isStreaming ? (
            <button
              type="button"
              className="composer__send composer__send--stop"
              onClick={handleStop}
              aria-label="중단"
            >
              <IconStop />
            </button>
          ) : (
            <button
              type="submit"
              className="composer__send"
              disabled={!userMessage.trim()}
              aria-label="보내기"
            >
              <IconSend />
            </button>
          )}
        </form>
        {showSuggestions && (
          <div className="composer__suggest">
            {EMPTY_SUGGESTIONS.map((s) => (
              <button
                key={s.text}
                type="button"
                className="composer__sug"
                onClick={() => callAgent(s.text, { user_message: s.text })}
              >
                <span className="composer__sug-emoji" aria-hidden>
                  {s.emoji}
                </span>
                {s.text}
              </button>
            ))}
          </div>
        )}
      </div>

      {debugInfo && (
        <details className="session__debug">
          <summary>Debug Info</summary>
          <p>Tool calls: {debugInfo.tool_calls.join(' → ') || '(없음)'}</p>
          <p>Latency: {debugInfo.latency_ms}ms</p>
        </details>
      )}
    </div>
  );
}

function reduceBlocks(blocks: Block[], event: AgentEvent): Block[] {
  switch (event.type) {
    case 'message_start': {
      const msg: Block = { type: 'message', id: event.id, text: '', streaming: true };
      return [...blocks, msg];
    }

    case 'message_delta':
      return blocks.map((b) =>
        b.type === 'message' && b.id === event.id ? { ...b, text: b.text + event.text } : b,
      );

    case 'message_end':
      return blocks.map((b) =>
        b.type === 'message' && b.id === event.id ? { ...b, streaming: false } : b,
      );

    case 'tool_status': {
      if (event.state === 'start') {
        const next: Block = {
          type: 'tool_status',
          tool: event.tool,
          state: 'running',
          input: event.input,
        };
        return [...blocks, next];
      }
      return collapseReasoning(flipLatestToolStatus(blocks, event.tool, event.result));
    }

    case 'reasoning_start': {
      const next: Block = {
        type: 'reasoning',
        id: event.id,
        text: '',
        streaming: true,
      };
      return [...blocks, next];
    }

    case 'reasoning_delta':
      return blocks.map((b) =>
        b.type === 'reasoning' && b.id === event.id
          ? { ...b, text: b.text + event.text }
          : b,
      );

    case 'reasoning_end':
      return blocks.map((b) =>
        b.type === 'reasoning' && b.id === event.id ? { ...b, streaming: false } : b,
      );

    case 'session':
    case 'done':
    case 'error':
      return blocks;

    default:
      // 세션 5 atomic block (recommendation_card, form 등) append
      return [...blocks, event as Block];
  }
}

// 진행 중인 블록이 하나라도 있으면 "생각중 인디케이터" 를 숨긴다.
function hasActiveBlock(blocks: Block[]): boolean {
  const last = blocks[blocks.length - 1];
  if (!last) return false;
  if (last.type === 'message' && last.streaming) return true;
  if (last.type === 'reasoning' && last.streaming) return true;
  if (last.type === 'tool_status' && last.state === 'running') return true;
  return false;
}

function flipLatestToolStatus(blocks: Block[], tool: string, result?: unknown): Block[] {
  for (let i = blocks.length - 1; i >= 0; i--) {
    const b = blocks[i];
    if (b.type === 'tool_status' && b.tool === tool && b.state === 'running') {
      const next = blocks.slice();
      next[i] = { ...b, state: 'done', collapsed: true, result };
      return next;
    }
  }
  return blocks;
}

function mergeMapPinsIntoCards(blocks: Block[]): Block[] {
  const pinsByName = new Map<string, { walk_minutes?: number; distance_m?: number }>();
  const cardNames = new Set<string>();
  for (const b of blocks) {
    if (b.type === 'recommendation_card') cardNames.add(b.restaurant.name);
  }
  for (const b of blocks) {
    if (b.type === 'map_pin' && cardNames.has(b.name)) {
      pinsByName.set(b.name, { walk_minutes: b.walk_minutes, distance_m: b.distance_m });
    }
  }
  if (pinsByName.size === 0) return blocks;
  return blocks
    .filter((b) => !(b.type === 'map_pin' && pinsByName.has(b.name)))
    .map((b) => {
      if (b.type !== 'recommendation_card') return b;
      const pin = pinsByName.get(b.restaurant.name);
      if (!pin) return b;
      return {
        ...b,
        restaurant: {
          ...b.restaurant,
          walk_minutes: b.restaurant.walk_minutes ?? pin.walk_minutes,
          distance_m: b.restaurant.distance_m ?? pin.distance_m,
        },
      };
    });
}

// 진행 중이던 message / reasoning / tool_status 를 모두 종료 상태로 전환한다.
function finalizeStreaming(blocks: Block[]): Block[] {
  let changed = false;
  const next = blocks.map((b) => {
    if ((b.type === 'message' || b.type === 'reasoning') && b.streaming) {
      changed = true;
      return { ...b, streaming: false };
    }
    if (b.type === 'tool_status' && b.state === 'running') {
      changed = true;
      return { ...b, state: 'done' as const, collapsed: true };
    }
    return b;
  });
  return changed ? next : blocks;
}

function collapseReasoning(blocks: Block[]): Block[] {
  let changed = false;
  const next = blocks.map((b) => {
    if (b.type === 'reasoning' && !b.collapsed && !b.streaming) {
      changed = true;
      return { ...b, collapsed: true };
    }
    return b;
  });
  return changed ? next : blocks;
}
