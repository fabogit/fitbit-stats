import { useEffect } from "react";
import { isTauri } from "@tauri-apps/api/core";
import { useAppDispatch } from "@/store/store";
import { openStatusSocket, waitForServer } from "@/lib/api";
import { loadJobStatus } from "./jobApi";
import { snapshotReceived, type JobSnapshot } from "./jobSlice";

const RECONNECT_MIN_MS = 1_000;
const RECONNECT_MAX_MS = 10_000;

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      clearTimeout(timer);
      resolve();
    });
  });
}

/**
 * Keeps `state.job` in step with the server, for the whole life of the app.
 *
 * Reads GET /api/status, then opens the status WebSocket, which sends the
 * current snapshot at once and again on every change. When the socket closes
 * (server restart, network) it reconnects after a growing wait and reads the
 * status again, since changes while disconnected are not replayed.
 */
export function useJobStatus() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    let socket: WebSocket | null = null;

    const run = async () => {
      // A cold desktop sidecar needs a few seconds before it answers. If it does
      // not in time, the loop below keeps trying with a growing wait.
      if (isTauri()) await waitForServer(signal);
      let delay = RECONNECT_MIN_MS;
      while (!signal.aborted) {
        try {
          await loadJobStatus(dispatch);
          const ws = await openStatusSocket();
          if (signal.aborted) {
            ws.close();
            return;
          }
          socket = ws;
          await new Promise<void>((resolve) => {
            ws.onopen = () => {
              delay = RECONNECT_MIN_MS;
            };
            ws.onmessage = (event) => {
              try {
                dispatch(snapshotReceived(JSON.parse(event.data) as JobSnapshot));
              } catch (e) {
                console.error("Error parsing status message:", e);
              }
            };
            ws.onclose = () => resolve();
          });
        } catch (e) {
          console.warn("Job status unavailable:", e);
        }
        socket = null;
        await sleep(delay, signal);
        delay = Math.min(delay * 2, RECONNECT_MAX_MS);
      }
    };
    void run();

    return () => {
      controller.abort();
      socket?.close();
    };
  }, [dispatch]);
}
