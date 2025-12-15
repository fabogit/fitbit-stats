import { useEffect, useState } from "react";
import { useAppDispatch, useAppSelector } from "./store/store";
import { fetchHealthData } from "./features/dashboard/dashboardSlice";
import { Sidebar } from "./components/dashboard/Sidebar";
import { OverviewView } from "./components/dashboard/views/OverviewView";
import { TimelineView } from "./components/dashboard/views/TimelineView";
import { AnalyticsView } from "./components/dashboard/views/AnalyticsView";
import { DataGridView } from "./components/dashboard/views/DataGridView";
import { PanelLeftOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeManager } from "./components/theme/ThemeManager";

function App() {
  const dispatch = useAppDispatch();
  const { status, error } = useAppSelector((state) => state.dashboard);
  const [activeTab, setActiveTab] = useState("overview");
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== "undefined") {
      return window.innerWidth >= 768;
    }
    return true;
  });

  useEffect(() => {
    dispatch(fetchHealthData());
  }, [dispatch]);

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  };

  const renderContent = () => {
    if (status === "loading") {
      return (
        <div className="min-h-screen bg-background flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        </div>
      );
    }

    if (status === "failed") {
      return (
        <div className="min-h-screen bg-background p-10 text-destructive">
          Critical Error: {error}
        </div>
      );
    }

    return (
      <div className="min-h-screen bg-background text-foreground font-sans overflow-x-hidden flex relative">
        {/* --- MOBILE BACKDROP OVERLAY --- */}
        {isSidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-40 md:hidden animate-in fade-in duration-200"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}

        {/* --- SIDEBAR --- */}
        <div
          className={cn(
            "fixed top-0 left-0 h-full z-50 w-64 bg-card border-r border-border transition-transform duration-300 ease-in-out shadow-xl md:shadow-none",
            isSidebarOpen ? "translate-x-0" : "-translate-x-full"
          )}
        >
          <Sidebar
            currentTab={activeTab}
            onTabChange={handleTabChange}
            onClose={() => setIsSidebarOpen(false)}
          />
        </div>

        {/* --- MAIN CONTENT --- */}
        <main
          className={cn(
            "flex-1 min-h-screen transition-all duration-300 ease-in-out",
            // Responsive Layout Logic
            isSidebarOpen ? "md:ml-64" : "ml-0"
          )}
        >
          {/* Header Mobile */}
          <div className="p-4 md:hidden flex items-center sticky top-0 bg-background/95 backdrop-blur z-30 border-b border-border">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="p-2 rounded-lg bg-card text-muted-foreground hover:text-foreground border border-border shadow-sm"
            >
              <PanelLeftOpen className="w-5 h-5" />
            </button>
            <span className="ml-3 font-semibold text-lg">FitStats</span>
          </div>

          {!isSidebarOpen && (
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="hidden md:block fixed top-4 left-4 p-2 rounded-lg bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition-colors border border-border z-40 shadow-lg animate-in fade-in zoom-in duration-200"
              title="Open Sidebar"
            >
              <PanelLeftOpen className="w-5 h-5" />
            </button>
          )}

          {/* Views*/}
          <div className="max-w-7xl mx-auto p-4 md:p-8 md:pt-4">
            {activeTab === "overview" && <OverviewView />}
            {activeTab === "timeline" && <TimelineView />}
            {activeTab === "analytics" && <AnalyticsView />}
            {activeTab === "datagrid" && <DataGridView />}
          </div>
        </main>
      </div>
    );
  };

  return (
    <>
      <ThemeManager />
      {renderContent()}
    </>
  );
}

export default App;
