import { Settings, PanelLeftOpen, PanelLeftClose } from "lucide-react";
import { ModeToggle } from "@/components/mode-toggle";

interface HeaderProps {
  activeTab: string;
  isSidebarOpen: boolean;
  setIsSidebarOpen: (open: boolean) => void;
  onRecalculate: () => void;
}

export function Header({
  activeTab,
  isSidebarOpen,
  setIsSidebarOpen,
  onRecalculate,
}: HeaderProps) {
  // Map tab IDs to user-friendly labels
  const tabLabels: Record<string, string> = {
    overview: "Overview",
    timeline: "Timeline",
    analytics: "Analytics",
    brief: "Daily Brief",
    datagrid: "Data Grid",
  };

  const currentTitle = tabLabels[activeTab] || "Dashboard";

  return (
    <header className="sticky top-0 z-40 w-full bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b border-border h-16 flex items-center px-4 md:px-8">
      {/* Left Section: Recalculate */}
      <div className="flex-1 flex items-center">
        <button
          onClick={onRecalculate}
          className="p-2 rounded-lg bg-muted/50 text-muted-foreground hover:text-foreground hover:bg-muted transition-all border border-transparent hover:border-border group"
          title="Recalculate / Settings"
        >
          <Settings className="w-5 h-5 group-hover:rotate-45 transition-transform duration-300" />
        </button>
      </div>

      {/* Center Section: App Title & Dynamic View Name */}
      <div className="flex-[2] flex items-center justify-center">
        <h2 className="text-sm md:text-base font-semibold tracking-tight text-center">
          <span className="text-muted-foreground font-normal">FitStats</span>
          <span className="mx-2 text-border">—</span>
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">
            {currentTitle}
          </span>
        </h2>
      </div>

      {/* Right Section: Theme & Sidebar Toggle */}
      <div className="flex-1 flex items-center justify-end gap-2">
        <ModeToggle />
        <button
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="p-2 rounded-lg bg-muted/50 text-muted-foreground hover:text-foreground hover:bg-muted transition-all border border-transparent hover:border-border"
          title={isSidebarOpen ? "Close Sidebar" : "Open Sidebar"}
        >
          {isSidebarOpen ? (
            <PanelLeftClose className="w-5 h-5" />
          ) : (
            <PanelLeftOpen className="w-5 h-5" />
          )}
        </button>
      </div>
    </header>
  );
}
