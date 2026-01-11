import { useEffect, useState, useCallback } from "react";
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

  const handleTabChange = useCallback((tab: string) => {
    setActiveTab(tab);
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  }, []);

  const handleCloseSidebar = useCallback(() => {
    setIsSidebarOpen(false);
  }, []);

  const renderContent = () => {
    return (
      <div className="min-h-screen bg-background text-foreground font-sans overflow-x-hidden flex relative">
        {/* --- MOBILE BACKDROP OVERLAY --- */}
        {isSidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-40 md:hidden animate-in fade-in duration-200"
            onClick={handleCloseSidebar}
          />
        )}

        {/* --- SIDEBAR --- */}
        <div
          className={cn(
            "fixed top-0 left-0 h-full z-50 w-64 bg-card border-r border-border transition-transform duration-300 ease-in-out shadow-xl md:shadow-none",
            isSidebarOpen ? "translate-x-0" : "-translate-x-full"
          )}
        >
          {/* OPTIMIZATION: Memoized Sidebar with stable callbacks to prevent re-renders */}
          <Sidebar
            currentTab={activeTab}
            onTabChange={handleTabChange}
            onClose={handleCloseSidebar}
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

          {/* Views Area with Loading/Error Handling */}
          <div className="max-w-7xl mx-auto p-4 md:p-8 md:pt-4">
            {status === "loading" ? (
              <div className="flex items-center justify-center h-[50vh]">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
              </div>
            ) : status === "failed" ? (
              <div className="p-10 text-destructive text-center">
                <h3 className="text-lg font-bold">Error loading data</h3>
                <p>{error}</p>
              </div>
            ) : (
              <>
                {activeTab === "overview" && <OverviewView />}
                {activeTab === "timeline" && <TimelineView />}
                {activeTab === "analytics" && <AnalyticsView />}
                {activeTab === "datagrid" && <DataGridView />}
              </>
            )}
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
