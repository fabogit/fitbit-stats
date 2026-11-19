import { useEffect, useState } from "react";
import { useAppDispatch, useAppSelector } from "./store/store";
import { fetchHealthData } from "./features/dashboard/dashboardSlice";
import { apiFetch, waitForServer } from "@/lib/api";
import { loadJobStatus } from "./features/job/jobApi";
import { useJobStatus } from "./features/job/useJobStatus";
import { Sidebar } from "./components/dashboard/Sidebar";
import { OverviewView } from "./components/dashboard/views/OverviewView";
import { TimelineView } from "./components/dashboard/views/TimelineView";
import { AnalyticsView } from "./components/dashboard/views/AnalyticsView";
import { cn } from "@/lib/utils";
import { DataGridView } from "./components/dashboard/views/DataGridView";
import { BriefView } from "./components/dashboard/views/BriefView";
import { SettingsModal } from "./components/dashboard/SettingsModal";
import { EtlProgressBanner } from "./components/dashboard/EtlProgressBanner";
import { EtlWarningsBanner } from "./components/dashboard/EtlWarningsBanner";
import { DataErrorState } from "./components/dashboard/DataErrorState";
import { Header } from "./components/dashboard/Header";
import { LandingPage } from "./components/onboarding/LandingPage";
import { StartupScreen } from "./components/dashboard/StartupScreen";

/** Where the start sequence is: waiting for the server, failed, first run, or the dashboard. */
type Startup = "starting" | "unreachable" | "first-run" | "ready";

function App() {
  const dispatch = useAppDispatch();
  const { status, filteredData } = useAppSelector((state) => state.dashboard);
  const [activeTab, setActiveTab] = useState("overview");
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [startup, setStartup] = useState<Startup>("starting");
  const [startAttempt, setStartAttempt] = useState(0);
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== "undefined") {
      return window.innerWidth >= 768;
    }
    return true;
  });

  // Keeps state.job in step with the server for the whole life of the app.
  useJobStatus();

  // Start sequence, the same on desktop and web: wait for the server, read the
  // job status, read the configuration, then load the data. The first-run page
  // is for a user with neither a saved configuration nor any data.
  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    const start = async () => {
      setStartup("starting");
      if (!(await waitForServer(signal))) {
        if (!signal.aborted) setStartup("unreachable");
        return;
      }
      try {
        // The run that is current when the data is loaded is the baseline for
        // reloading it later (see the job listener). A failed read is not fatal:
        // the status connection keeps trying and the data read below reports
        // a server that is really down.
        await loadJobStatus(dispatch).catch((e) => console.warn("Job status unavailable:", e));
        const resp = await apiFetch("/api/config");
        if (!resp.ok) throw new Error(`Config request failed (HTTP ${resp.status})`);
        const configData = await resp.json();
        if (signal.aborted) return;
        const result = await dispatch(fetchHealthData());
        if (signal.aborted) return;
        const noConfig = !configData || !configData.dob;
        const noData = fetchHealthData.fulfilled.match(result) && result.payload.length === 0;
        // A failed load is shown by the dashboard as an error, never as "no data".
        setStartup(noConfig && noData ? "first-run" : "ready");
      } catch (e) {
        console.error("Start sequence failed:", e);
        if (!signal.aborted) setStartup("unreachable");
      }
    };
    void start();
    return () => controller.abort();
  }, [dispatch, startAttempt]);

  const handleInitialConfigSuccess = () => {
    setStartup("ready");
    // The data is loaded by the job listener when the run that was just started finishes.
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
    if (startup === "starting" || startup === "unreachable") {
      return <StartupScreen kind={startup} onRetry={() => setStartAttempt((n) => n + 1)} />;
    }

    if (startup === "ready" && status === "loading" && filteredData.length === 0) {
      return (
        <div className="min-h-screen bg-background flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        </div>
      );
    }

    if (startup === "first-run") {
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
            {/* NoDataState draws its own progress when there is nothing to show */}
            {filteredData.length > 0 && <EtlProgressBanner />}
            <EtlWarningsBanner />
            <div className="p-4 md:p-8 flex-1">
              {status === "failed" ? (
                <DataErrorState onRecalculate={() => setIsSettingsOpen(true)} />
              ) : (
                <>
                  {activeTab === "overview" && <OverviewView onAction={() => setIsSettingsOpen(true)} />}
                  {activeTab === "timeline" && <TimelineView onAction={() => setIsSettingsOpen(true)} />}
                  {activeTab === "analytics" && <AnalyticsView onAction={() => setIsSettingsOpen(true)} />}
                  {activeTab === "brief" && <BriefView onAction={() => setIsSettingsOpen(true)} />}
                  {activeTab === "datagrid" && <DataGridView onAction={() => setIsSettingsOpen(true)} />}
                </>
              )}
            </div>
          </main>
        </div>
      </div>
    );
  };

  return renderContent();
}

export default App;
