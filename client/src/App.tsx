import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "./store";
import { fetchHealthData } from "./features/dashboard/dashboardSlice";
import { Header } from "./components/dashboard/Header";
import { KpiGrid } from "./components/dashboard/KpiGrid";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TimelineView } from "./components/dashboard/views/TimelineView";
import { AnalyticsView } from "./components/dashboard/views/AnalyticsView";

function App() {
  const dispatch = useAppDispatch();
  const { status, error } = useAppSelector((state) => state.dashboard);

  useEffect(() => {
    dispatch(fetchHealthData());
  }, [dispatch]);

  if (status === "loading")
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">
        Loading...
      </div>
    );
  if (status === "failed")
    return (
      <div className="min-h-screen bg-slate-950 p-10 text-red-500">
        Error: {error}
      </div>
    );

  return (
    <div className="min-h-screen bg-slate-950 p-4 md:p-8 text-slate-50">
      <div className="max-w-7xl mx-auto space-y-6">
        <Header />
        <KpiGrid />

        {/* TABS NAVIGATION */}
        <Tabs defaultValue="timeline" className="w-full">
          <div className="flex justify-center mb-6">
            <TabsList className="bg-slate-900 border border-slate-800">
              <TabsTrigger value="timeline">Timeline (Daily)</TabsTrigger>
              <TabsTrigger value="analytics">Analytics (Insights)</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="timeline">
            <TimelineView />
          </TabsContent>

          <TabsContent value="analytics">
            <AnalyticsView />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export default App;
