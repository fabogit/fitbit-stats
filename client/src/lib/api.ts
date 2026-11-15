/**
 * Centralized API base URL.
 *
 * We use 127.0.0.1 explicitly instead of "localhost" to avoid the IPv6
 * resolution issue on Windows where "localhost" may resolve to "::1" (IPv6)
 * while the uvicorn server only listens on 127.0.0.1 (IPv4), causing
 * WebSocket and HTTP connections to fail silently.
 */
export const SERVER_URL = {
  API: "http://127.0.0.1:8000",
  WS: "ws://127.0.0.1:8000",
};


/**
 * Wait until the local API answers `/api/health`.
 *
 * A cold sidecar needs a few seconds to unpack and start, so the first
 * requests would otherwise fail. Polls every `intervalMs` until `timeoutMs`
 * has elapsed; resolves `true` once the server is up and `false` on timeout
 * or abort.
 */
export async function waitForServer(
  signal?: AbortSignal,
  timeoutMs = 60_000,
  intervalMs = 500,
): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (!signal?.aborted && Date.now() < deadline) {
    const attempt = new AbortController();
    const timer = setTimeout(() => attempt.abort(), 2_000);
    try {
      const resp = await fetch(`${SERVER_URL.API}/api/health`, {
        signal: attempt.signal,
      });
      if (resp.ok) return true;
    } catch {
      // not up yet: retry below
    } finally {
      clearTimeout(timer);
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return false;
}
