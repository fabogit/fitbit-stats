import { invoke, isTauri } from "@tauri-apps/api/core";
import { fetchServerInfo, onServerState } from "@/lib/desktopServer";

/**
 * Where the API is. The only place that tells the desktop app from the web
 * build.
 *
 * Desktop: the sidecar listens on a free port that it picks itself and tells
 * the shell about; the shell passes it on (see `desktopServer.ts`). We use
 * 127.0.0.1 explicitly instead of "localhost" to avoid the IPv6 resolution
 * issue on Windows where "localhost" may resolve to "::1" (IPv6) while the
 * uvicorn server only listens on 127.0.0.1 (IPv4), causing WebSocket and HTTP
 * connections to fail silently.
 *
 * Web (Docker, and `pnpm dev` through the Vite proxy): the page and the API
 * share one origin, so requests are relative and the WebSocket URL follows
 * the page's own address. Nginx (or Vite) forwards `/api` and `/ws`.
 */
interface Endpoint {
  API: string;
  WS: string;
}

const WEB_ENDPOINT: Endpoint = {
  API: "",
  WS: `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`,
};

let endpointCache: Endpoint | null = null;
// Counts the changes the shell has reported, so an answer that was already on
// its way when the server changed is not kept.
let serverChanges = 0;
let watchingServer = false;

/**
 * The address of the API. On the desktop it is asked of the shell, kept for
 * as long as that server runs and forgotten when the shell reports a change
 * (a restarted server has another port). Throws while the server is not up.
 */
async function getEndpoint(): Promise<Endpoint> {
  if (!isTauri()) return WEB_ENDPOINT;
  if (!watchingServer) {
    watchingServer = true;
    onServerState(() => {
      serverChanges++;
      endpointCache = null;
    });
  }
  if (endpointCache) return endpointCache;
  const seen = serverChanges;
  const info = await fetchServerInfo();
  if (info.state === "ready" && info.port) {
    const endpoint = {
      API: `http://127.0.0.1:${info.port}`,
      WS: `ws://127.0.0.1:${info.port}`,
    };
    if (seen === serverChanges) endpointCache = endpoint;
    return endpoint;
  }
  throw new Error(
    info.state === "failed"
      ? (info.message ?? "The local server is not running.")
      : "The local server is still starting.",
  );
}

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
  const [token, endpoint] = await Promise.all([getApiToken(), getEndpoint()]);
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${endpoint.API}${path}`, { ...init, headers });
}

/** Opens the status WebSocket, passing the token (if any) as a subprotocol. */
export async function openStatusSocket(): Promise<WebSocket> {
  const [token, endpoint] = await Promise.all([getApiToken(), getEndpoint()]);
  const url = `${endpoint.WS}/ws/status`;
  return token ? new WebSocket(url, ["fitstats", `token.${token}`]) : new WebSocket(url);
}

/**
 * Wait until the local API answers `/api/health`.
 *
 * A cold sidecar needs a few seconds to unpack and start, so the first
 * requests would otherwise fail. Polls every `intervalMs` until `timeoutMs`
 * has elapsed (then once more); resolves `true` once the server is up and
 * `false` on timeout or abort.
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
  if (signal?.aborted) return false;
  // One last try: the server may have become ready in the half second the loop was asleep.
  try {
    return (await apiFetch("/api/health")).ok;
  } catch {
    return false;
  }
}
