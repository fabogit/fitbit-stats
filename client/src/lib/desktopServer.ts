import { useEffect, useState, useSyncExternalStore } from "react";
import { invoke, isTauri } from "@tauri-apps/api/core";
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

// --- What the interface knows about the server ---------------------------------

interface ServerView {
  info: ServerInfo | null;
  /** True once the server has been ready at least once in this session. */
  everReady: boolean;
}

let view: ServerView = { info: null, everReady: false };
const listeners = new Set<() => void>();
let watching = false;

const RANK = { starting: 0, ready: 1, failed: 1 } as const;

/** Keeps the newest report: later generations win, and within one a start is never news after its end. */
function apply(info: ServerInfo): void {
  const old = view.info;
  if (old && (info.generation < old.generation ||
      (info.generation === old.generation && RANK[info.state] < RANK[old.state]))) {
    return;
  }
  view = { info, everReady: view.everReady || info.state === "ready" };
  listeners.forEach((listener) => listener());
}

function startWatching(): void {
  if (watching || !isTauri()) return;
  watching = true;
  // Listen first, then ask: a change in between is not lost, and apply() orders the two.
  onServerState(apply);
  fetchServerInfo().then(apply).catch((e) => console.warn("Server state unavailable:", e));
}

function subscribe(listener: () => void): () => void {
  startWatching();
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

const getView = () => view;

/** The state of the desktop server, live. `null` in the web build, which has no desktop server. */
export function useDesktopServer(): ServerView | null {
  const current = useSyncExternalStore(subscribe, getView);
  return isTauri() ? current : null;
}

/** Waits `ms`, or less if the server becomes ready, or until `signal` aborts. */
export function sleepUntilServerReady(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      stop();
      signal.removeEventListener("abort", finish);
      resolve();
    };
    const timer = setTimeout(finish, ms);
    const stop = subscribe(() => {
      if (view.info?.state === "ready") finish();
    });
    signal.addEventListener("abort", finish);
  });
}

/** Starts the server again (the button of the failure screens). */
export function restartServer(): Promise<void> {
  return invoke<void>("restart_server");
}

/** Full path of the log file, `null` if the shell cannot say. */
export function getLogLocation(): Promise<string | null> {
  return invoke<string>("log_location").catch(() => null);
}

/** Where the log file is, for the failure screens; `null` until the shell says. */
export function useLogLocation(enabled: boolean): string | null {
  const [path, setPath] = useState<string | null>(null);
  useEffect(() => {
    if (!enabled || path) return;
    let current = true;
    void getLogLocation().then((location) => {
      if (current) setPath(location);
    });
    return () => {
      current = false;
    };
  }, [enabled, path]);
  return path;
}
