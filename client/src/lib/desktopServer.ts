import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

/**
 * What the desktop shell says about the local server. Sent at every change as
 * the `server-state` event and as the answer of `server_endpoint`.
 * `generation` grows with every start of the server.
 */
export interface ServerInfo {
  generation: number;
  state: "starting" | "ready" | "failed";
  port?: number;
  message?: string;
}

/**
 * The state of the server. While it is starting, the shell waits a moment for
 * it to be ready before answering, so the first request is not sent too early.
 */
export function fetchServerInfo(): Promise<ServerInfo> {
  return invoke<ServerInfo>("server_endpoint");
}

/** Calls `listener` at every change of the server state. Returns the way to stop. */
export function onServerState(listener: (info: ServerInfo) => void): () => void {
  let stopped = false;
  let unlisten: (() => void) | null = null;
  listen<ServerInfo>("server-state", (event) => listener(event.payload)).then((fn) => {
    if (stopped) fn();
    else unlisten = fn;
  });
  return () => {
    stopped = true;
    unlisten?.();
  };
}
