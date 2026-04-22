// 단건 JSON 요청 기본 timeout
const DEFAULT_TIMEOUT_MS = 20_000;

/** fetch 래퍼 — 응답이 200 대가 아니면 에러를 던지고, 성공 시 JSON 을 파싱해 반환한다. */
export async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const timeoutSignal = AbortSignal.timeout(DEFAULT_TIMEOUT_MS);
  const signal = init?.signal
    ? AbortSignal.any([init.signal, timeoutSignal])
    : timeoutSignal;
  try {
    const res = await fetch(url, {
      ...init,
      headers: { Accept: 'application/json', ...(init?.headers || {}) },
      signal,
    });
    if (!res.ok) {
      throw new Error(`${url} failed: ${res.status}`);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === 'TimeoutError') {
      throw new Error('응답이 지연되고 있어요. 잠시 후 다시 시도해주세요.');
    }
    throw err;
  }
}
