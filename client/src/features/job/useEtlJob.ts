import { useCallback, useState } from "react";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { selectIsRunning } from "./jobSlice";
import { startJob, type StartBody } from "./startJob";

export type StartOutcome =
  | { kind: "started" }
  /** The server was already running a calculation; the store now shows it. */
  | { kind: "busy" }
  /** The server refused, or could not be reached. */
  | { kind: "failed"; message: string };

export interface EtlJob {
  /** Asks the server to start a calculation. Never throws. */
  start(body: StartBody): Promise<StartOutcome>;
  /** The start request is in flight. */
  starting: boolean;
  /** A calculation is running, as the job status in the store says. */
  running: boolean;
}

/** Shown when the start of a calculation is not accepted. */
const failedMessage = (status: number) =>
  `Could not start the calculation (HTTP ${status}). Check that the server is running and try again.`;
const UNREACHABLE_MESSAGE = "Could not reach the local server. Check that it is running and try again.";

/**
 * Starting a calculation as the forms see it: a request that is in flight, and
 * an outcome with a message to show. Progress and the end of the run are not
 * here: they come from the job status (see `useJobStatus`).
 */
export function useEtlJob(): EtlJob {
  const dispatch = useAppDispatch();
  const running = useAppSelector(selectIsRunning);
  const [starting, setStarting] = useState(false);

  const start = useCallback(
    async (body: StartBody): Promise<StartOutcome> => {
      setStarting(true);
      try {
        const result = await startJob(dispatch, body);
        if (result.kind === "failed") {
          return { kind: "failed", message: failedMessage(result.status) };
        }
        return result;
      } catch (err) {
        console.error("Start request failed:", err);
        return { kind: "failed", message: UNREACHABLE_MESSAGE };
      } finally {
        setStarting(false);
      }
    },
    [dispatch],
  );

  return { start, starting, running };
}
