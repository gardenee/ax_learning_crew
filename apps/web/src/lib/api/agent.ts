import type { AgentEvent, AgentRunRequest } from '../types/api';

const API_BASE = '/api';
const IDLE_TIMEOUT_MS = 120_000;

export async function* streamAgent(
  request: AgentRunRequest,
  signal?: AbortSignal,
): AsyncIterable<AgentEvent> {
  const idleCtrl = new AbortController();
  let idleTimer: ReturnType<typeof setTimeout> | null = null;
  const resetIdle = () => {
    if (idleTimer) clearTimeout(idleTimer);
    idleTimer = setTimeout(
      () =>
        idleCtrl.abort(
          new DOMException(
            '응답이 지연되고 있어요. 잠시 후 다시 시도해주세요.',
            'TimeoutError',
          ),
        ),
      IDLE_TIMEOUT_MS,
    );
  };

  const forwardAbort = () => idleCtrl.abort(signal?.reason);
  if (signal?.aborted) idleCtrl.abort(signal.reason);
  else signal?.addEventListener('abort', forwardAbort);

  resetIdle();

  try {
    const res = await fetch(`${API_BASE}/agent/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(request),
      signal: idleCtrl.signal,
    });

    if (!res.ok || !res.body) {
      const body = await res.text().catch(() => '');
      throw new Error(`Agent API error ${res.status}: ${body}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        resetIdle();

        buffer += decoder.decode(value, { stream: true });

        let sep = buffer.indexOf('\n\n');
        while (sep !== -1) {
          const raw = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          sep = buffer.indexOf('\n\n');

          const data = raw
            .split('\n')
            .filter((line) => line.startsWith('data:'))
            .map((line) => line.slice(5).replace(/^\s/, ''))
            .join('\n');

          if (!data) continue;

          try {
            yield JSON.parse(data) as AgentEvent;
          } catch (err) {
            console.error('[streamAgent] SSE parse error', err, data);
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  } finally {
    if (idleTimer) clearTimeout(idleTimer);
    signal?.removeEventListener('abort', forwardAbort);
  }
}
