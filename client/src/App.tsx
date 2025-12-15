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
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  useEffect(() => {
    dispatch(fetchHealthData());
  }, [dispatch]);

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

    // Il contenuto principale dell'app
    return (
      <div className="min-h-screen bg-background text-foreground font-sans overflow-x-hidden flex">
        {/* SIDEBAR */}
        <div
          className={cn(
            "fixed top-0 left-0 h-full z-50 w-64 bg-card border-r border-border transition-transform duration-300 ease-in-out",
            isSidebarOpen ? "translate-x-0" : "-translate-x-full"
          )}
        >
          <Sidebar
            currentTab={activeTab}
            onTabChange={setActiveTab}
            onClose={() => setIsSidebarOpen(false)}
          />
        </div>

        {/* MAIN CONTENT */}
        <main
          className={cn(
            "flex-1 min-h-screen transition-all duration-300 ease-in-out p-8",
            isSidebarOpen ? "ml-64" : "ml-0"
          )}
        >
          {!isSidebarOpen && (
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="fixed top-4 left-4 p-2 rounded-lg bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition-colors border border-border z-40 shadow-lg animate-in fade-in zoom-in duration-200"
              title="Open Sidebar"
            >
              <PanelLeftOpen className="w-5 h-5" />
            </button>
          )}

          <div className="max-w-7xl mx-auto pt-4">
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
