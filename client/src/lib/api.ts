import { invoke, isTauri } from "@tauri-apps/api/core";

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

let tokenPromise: Promise<string | null> | null = null;

/**
 * Per-launch API token issued by the desktop shell. The web build has none
 * (null) and sends no token. Cached after the first successful read.
 */
function getApiToken(): Promise<string | null> {
  if (!isTauri()) return Promise.resolve(null);
  if (!tokenPromise) {
    tokenPromise = invoke<string>("get_api_token").catch((e) => {
      tokenPromise = null;
      throw e;
    });
  }
  return tokenPromise;
}

/** Single entry point for API requests: adds the token when there is one. */
export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const token = await getApiToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${SERVER_URL.API}${path}`, { ...init, headers });
}

/** Opens the status WebSocket, passing the token (if any) as a subprotocol. */
export async function openStatusSocket(): Promise<WebSocket> {
  const token = await getApiToken();
  const url = `${SERVER_URL.WS}/ws/status`;
  return token ? new WebSocket(url, ["fitstats", `token.${token}`]) : new WebSocket(url);
}

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
      const resp = await apiFetch("/api/health", {
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
