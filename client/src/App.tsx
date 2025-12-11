import { useEffect, useState } from "react";
import { useAppDispatch, useAppSelector } from "./store";
import { fetchHealthData } from "./features/dashboard/dashboardSlice";
import { Sidebar } from "./components/dashboard/Sidebar";
import { OverviewView } from "./components/dashboard/views/OverviewView";
import { TimelineView } from "./components/dashboard/views/TimelineView";
import { AnalyticsView } from "./components/dashboard/views/AnalyticsView";
import { PanelLeftOpen } from "lucide-react";
import { cn } from "@/lib/utils";

function App() {
  const dispatch = useAppDispatch();
  const { status, error } = useAppSelector((state) => state.dashboard);

  const [activeTab, setActiveTab] = useState("overview");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  useEffect(() => {
    dispatch(fetchHealthData());
  }, [dispatch]);

  if (status === "loading") {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="min-h-screen bg-slate-950 p-10 text-red-500">
        Critical Error: {error}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 font-sans overflow-x-hidden flex">
      {/* 1. SIDEBAR*/}
      <div
        className={cn(
          "fixed top-0 left-0 h-full z-50 w-64 bg-slate-900 border-r border-slate-800 transition-transform duration-300 ease-in-out",
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <Sidebar
          currentTab={activeTab}
          onTabChange={setActiveTab}
          onClose={() => setIsSidebarOpen(false)} // <--- Nuova Prop
        />
      </div>

      {/* 2. MAIN CONTENT */}
      <main
        className={cn(
          "flex-1 min-h-screen transition-all duration-300 ease-in-out p-8",
          isSidebarOpen ? "ml-64" : "ml-0"
        )}
      >
        {!isSidebarOpen && (
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="fixed top-4 left-4 p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors border border-slate-700 z-40 shadow-lg animate-in fade-in zoom-in duration-200"
            title="Open Sidebar"
          >
            <PanelLeftOpen className="w-5 h-5" />
          </button>
        )}

        <div className="max-w-7xl mx-auto">
          {activeTab === "overview" && <OverviewView />}
          {activeTab === "timeline" && <TimelineView />}
          {activeTab === "analytics" && <AnalyticsView />}
        </div>
      </main>
    </div>
  );
}

export default App;
