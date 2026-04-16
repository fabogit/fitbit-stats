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

