import { useSyncExternalStore } from "react";
import { CheckCircle2, Info, X, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export type NoticeKind = "error" | "info" | "success";

export interface Notice {
  kind: NoticeKind;
  text: string;
}

const STYLES = {
  error: { box: "border-red-500/40 bg-red-500/10", color: "text-red-500", Icon: XCircle },
  info: { box: "border-sky-500/40 bg-sky-500/10", color: "text-sky-500", Icon: Info },
  success: {
    box: "border-green-500/40 bg-green-500/10",
    color: "text-green-500",
    Icon: CheckCircle2,
  },
} as const;

interface InlineNoticeProps {
  notice: Notice | null;
  onDismiss?: () => void;
  /** Adds the live-region role; off inside `NoticeRegion`, which is the live region. */
  live?: boolean;
  className?: string;
}

/** A message next to what it is about. Errors use role="alert", the rest role="status". */
export function InlineNotice({ notice, onDismiss, live = true, className }: InlineNoticeProps) {
  if (!notice) return null;
  const { box, color, Icon } = STYLES[notice.kind];
  return (
    <div
      role={live ? (notice.kind === "error" ? "alert" : "status") : undefined}
      data-testid={`notice-${notice.kind}`}
      className={cn("flex items-start gap-3 rounded-md border px-3 py-2", box, className)}
    >
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", color)} />
      <p className="min-w-0 flex-1 break-words text-sm">{notice.text}</p>
      {onDismiss && (
        <button
          type="button"
          aria-label="Dismiss"
          onClick={onDismiss}
          className="text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

// Notices that must outlive the component that raised them (a closed dialog).
interface Entry extends Notice {
  id: number;
}
let entries: Entry[] = [];
let nextId = 1;
const listeners = new Set<() => void>();

const emit = () => listeners.forEach((listener) => listener());
const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};
const getEntries = () => entries;

function dismiss(id: number) {
  entries = entries.filter((entry) => entry.id !== id);
  emit();
}

/**
 * Shows a notice in the `NoticeRegion` until the user dismisses it. The same
 * message is not stacked. Lives with the region it feeds (same exception as
 * button.tsx).
 */
// eslint-disable-next-line react-refresh/only-export-components
export function notify(notice: Notice): void {
  if (entries.some((entry) => entry.kind === notice.kind && entry.text === notice.text)) return;
  entries = [...entries, { ...notice, id: nextId++ }];
  emit();
}

/**
 * Where `notify` messages appear. Mounted once, before any message, so screen
 * readers announce what is added to it.
 */
export function NoticeRegion() {
  const list = useSyncExternalStore(subscribe, getEntries);
  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="notice-region"
      className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2"
    >
      {list.map((entry) => (
        <div key={entry.id} className="pointer-events-auto rounded-md bg-background shadow-lg">
          <InlineNotice notice={entry} live={false} onDismiss={() => dismiss(entry.id)} />
        </div>
      ))}
    </div>
  );
}
