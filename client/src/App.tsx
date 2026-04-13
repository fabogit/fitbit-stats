import { useEffect, useState } from "react";
import { useAppDispatch, useAppSelector } from "./store/store";
import { fetchHealthData } from "./features/dashboard/dashboardSlice";
import { Sidebar } from "./components/dashboard/Sidebar";
import { OverviewView } from "./components/dashboard/views/OverviewView";
import { TimelineView } from "./components/dashboard/views/TimelineView";
import { AnalyticsView } from "./components/dashboard/views/AnalyticsView";
import { cn } from "@/lib/utils";
import { DataGridView } from "./components/dashboard/views/DataGridView";
import { BriefView } from "./components/dashboard/views/BriefView";
import { SettingsModal } from "./components/dashboard/SettingsModal";
import { Header } from "./components/dashboard/Header";
import { LandingPage } from "./components/onboarding/LandingPage";
import { isTauri } from "@tauri-apps/api/core";
import { exists, BaseDirectory } from "@tauri-apps/plugin-fs";

function App() {
  const dispatch = useAppDispatch();
  const { status } = useAppSelector((state) => state.dashboard);
  const [activeTab, setActiveTab] = useState("overview");
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isFirstRun, setIsFirstRun] = useState<boolean | null>(null); // null = checking
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== "undefined") {
      return window.innerWidth >= 768;
    }
    return true;
  });

  useEffect(() => {
    // Check if configuration exists
    const checkConfig = async () => {
      try {
        if (isTauri()) {
          const hasData = await exists("dashboard_data.json", { baseDir: BaseDirectory.AppData });
          
          if (hasData) {
            setIsFirstRun(false);
            dispatch(fetchHealthData());
          } else {
            setIsFirstRun(true);
          }
        } else {
          const resp = await fetch("http://localhost:8000/api/config");
          const configData = await resp.json();
          
          if (!configData || !configData.dob) {
            setIsFirstRun(true);
          } else {
            setIsFirstRun(false);
            dispatch(fetchHealthData());
          }
        }
      } catch (e) {
        console.error("Failed to fetch config or read fs", e);
        // If we can't route or check, treat as first run
        setIsFirstRun(true);
      }
    };
    checkConfig();
  }, [dispatch]);

  const handleInitialConfigSuccess = () => {
    setIsFirstRun(false);
    // fetchHealthData is now automatically dispatched via WebSocket closure inside ConfigForm
  };

  const handleTabChange = (tab: string) => {
    if (tab === "settings") {
      setIsSettingsOpen(true);
      return;
    }
    setActiveTab(tab);
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  };

  const renderContent = () => {
    if (isFirstRun === null || (status === "loading" && !isFirstRun)) {
      return (
        <div className="min-h-screen bg-background flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        </div>
      );
    }

    if (isFirstRun) {
      return <LandingPage onSuccess={handleInitialConfigSuccess} />;
    }

    return (
      <div className="min-h-screen bg-background text-foreground font-sans overflow-x-hidden flex flex-col items-stretch relative">
        <SettingsModal isOpen={isSettingsOpen} onOpenChange={setIsSettingsOpen} />
        
        {/* --- GLOBAL HEADER (Full Width, Always Top) --- */}
        <Header
          activeTab={activeTab}
          isSidebarOpen={isSidebarOpen}
          setIsSidebarOpen={setIsSidebarOpen}
          onRecalculate={() => setIsSettingsOpen(true)}
        />

        <div className="flex flex-1 relative overflow-hidden h-[calc(100vh-64px)] mt-16">
          {/* --- MOBILE BACKDROP OVERLAY --- */}
          {isSidebarOpen && (
            <div
              className="fixed inset-0 bg-black/50 z-40 md:hidden animate-in fade-in duration-200"
              onClick={() => setIsSidebarOpen(false)}
            />
          )}

          {/* --- SIDEBAR (Starts below Header) --- */}
          <div
            className={cn(
              "fixed top-16 left-0 h-[calc(100vh-64px)] z-50 w-64 bg-card border-r border-border transition-transform duration-300 ease-in-out shadow-xl md:shadow-none",
              isSidebarOpen ? "translate-x-0" : "-translate-x-full"
            )}
          >
            <Sidebar
              currentTab={activeTab}
              onTabChange={handleTabChange}
            />
          </div>

          {/* --- MAIN CONTENT (Starts below Header) --- */}
          <main
            className={cn(
              "flex-1 min-h-full transition-all duration-300 ease-in-out flex flex-col overflow-y-auto mt-0 px-0",
              isSidebarOpen ? "md:ml-64" : "ml-0"
            )}
          >
            <div className="p-4 md:p-8 flex-1">
              {activeTab === "overview" && <OverviewView onAction={() => setIsSettingsOpen(true)} />}
              {activeTab === "timeline" && <TimelineView onAction={() => setIsSettingsOpen(true)} />}
              {activeTab === "analytics" && <AnalyticsView onAction={() => setIsSettingsOpen(true)} />}
              {activeTab === "brief" && <BriefView onAction={() => setIsSettingsOpen(true)} />}
              {activeTab === "datagrid" && <DataGridView />}
            </div>
          </main>
        </div>
      </div>
    );
  };

  return renderContent();
}

export default App;
