import { useEffect, useState } from "react";
import { useAppDispatch, useAppSelector } from "./store/store";
import { fetchHealthData } from "./features/dashboard/dashboardSlice";
import { Sidebar } from "./components/dashboard/Sidebar";
import { OverviewView } from "./components/dashboard/views/OverviewView";
import { TimelineView } from "./components/dashboard/views/TimelineView";
import { AnalyticsView } from "./components/dashboard/views/AnalyticsView";
import { DataGridView } from "./components/dashboard/views/DataGridView";
import { BriefView } from "./components/dashboard/views/BriefView";
import { PanelLeftOpen, PanelLeftClose } from "lucide-react";
import { cn } from "@/lib/utils";
import { SettingsModal } from "./components/dashboard/SettingsModal";
import { ModeToggle } from "./components/mode-toggle";
import { LandingPage } from "./components/onboarding/LandingPage";

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
        const resp = await fetch("http://localhost:8000/api/config");
        const configData = await resp.json();
        
        if (!configData || !configData.dob) {
          setIsFirstRun(true);
        } else {
          setIsFirstRun(false);
          dispatch(fetchHealthData());
        }
      } catch (e) {
        console.error("Failed to fetch config", e);
        // If we can't even reach the API, treat as first run or show onboarding
        setIsFirstRun(true);
      }
    };
    checkConfig();
  }, [dispatch]);

  const handleInitialConfigSuccess = () => {
    setIsFirstRun(false);
    dispatch(fetchHealthData());
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
      <div className="min-h-screen bg-background text-foreground font-sans overflow-x-hidden flex relative">
        <SettingsModal isOpen={isSettingsOpen} onOpenChange={setIsSettingsOpen} />
        
        {/* --- GLOBAL CONTROLS (Top Right) --- */}
        <div className="fixed top-4 right-4 z-[60] flex flex-col items-end gap-3">
          <ModeToggle />
           <button
             onClick={() => setIsSidebarOpen(!isSidebarOpen)}
             className="p-2 rounded-lg bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition-all border border-border shadow-lg"
             title={isSidebarOpen ? "Close Sidebar" : "Open Sidebar"}
           >
             {isSidebarOpen ? (
               <PanelLeftClose className="w-5 h-5" />
             ) : (
               <PanelLeftOpen className="w-5 h-5" />
             )}
           </button>
        </div>

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
          />
        </div>

        {/* --- MAIN CONTENT --- */}
        <main
          className={cn(
            "flex-1 min-h-screen transition-all duration-300 ease-in-out",
            isSidebarOpen ? "md:ml-64" : "ml-0"
          )}
        >
          {/* Header Mobile - Just the text, toggles are fixed right */}
          <div className="p-4 md:hidden flex items-center justify-center sticky top-0 bg-background/95 backdrop-blur z-30 border-b border-border h-16">
            <span className="font-semibold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">FitStats</span>
          </div>

          <div className="p-4 pt-20 md:p-8 md:pt-8 min-h-screen overflow-y-auto">
            {activeTab === "overview" && <OverviewView onAction={() => setIsSettingsOpen(true)} />}
            {activeTab === "timeline" && <TimelineView onAction={() => setIsSettingsOpen(true)} />}
            {activeTab === "analytics" && <AnalyticsView onAction={() => setIsSettingsOpen(true)} />}
            {activeTab === "brief" && <BriefView />}
            {activeTab === "datagrid" && <DataGridView />}
          </div>
        </main>
      </div>
    );
  };

  return renderContent();
}

export default App;
