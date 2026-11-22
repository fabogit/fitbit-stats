import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { restartServer, useDesktopServer, useLogLocation } from "@/lib/desktopServer";

/**
 * Tells the user that the local server stopped while the app is open: it is
 * being restarted, or it gave up and can be restarted by hand. A floating
 * message, not a screen: what is already on display stays readable.
 * Desktop only, and only after the server has been up once (the start has its
 * own screen).
 */
export function ServerBanner() {
  const server = useDesktopServer();
  const state = server?.info?.state;
  const shown = Boolean(server?.everReady) && (state === "starting" || state === "failed");
  const failed = state === "failed";
  const logPath = useLogLocation(shown && failed);
  if (!shown) return null;

  return (
    <div
      data-testid="server-banner-region"
      className="pointer-events-none fixed inset-x-0 top-3 z-[100] flex justify-center px-4"
    >
      {failed ? (
        <div
          role="alert"
          data-testid="server-banner-failed"
          className="pointer-events-auto flex w-full max-w-xl flex-col gap-2 rounded-md border border-red-500/40 bg-background px-4 py-3 shadow-lg"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
            <p className="min-w-0 flex-1 text-sm font-medium">The local server stopped</p>
            <Button size="sm" onClick={() => void restartServer().catch(console.error)}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Restart server
            </Button>
          </div>
          {logPath && (
            <p className="break-all text-xs text-muted-foreground">Log file: {logPath}</p>
          )}
        </div>
      ) : (
        <div
          role="status"
          data-testid="server-banner-restarting"
          className="pointer-events-auto flex items-center gap-3 rounded-md border border-amber-500/40 bg-background px-4 py-3 shadow-lg"
        >
          <Loader2 className="h-4 w-4 shrink-0 animate-spin text-amber-500" />
          <p className="text-sm font-medium">The local server stopped. Restarting…</p>
        </div>
      )}
    </div>
  );
}
