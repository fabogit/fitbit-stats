import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "./store";
import { fetchHealthData } from "./features/dashboard/dashboardSlice";
import { Header } from "./components/dashboard/Header";
import { KpiGrid } from "./components/dashboard/KpiGrid";

function App() {
  const dispatch = useAppDispatch();
  const { status, error } = useAppSelector((state) => state.dashboard);

  useEffect(() => {
    dispatch(fetchHealthData());
  }, [dispatch]);

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (status === "failed") {
    return <div className="p-10 text-red-500">Critical Error: {error}</div>;
  }

  return (
    <div className="min-h-screen p-4 md:p-8 max-w-7xl mx-auto">
      <Header />
      <main>
        <KpiGrid />

        {/* Placeholder */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          <div className="h-64 bg-slate-900/50 rounded-xl border border-slate-800 flex items-center justify-center text-slate-500 border-dashed">
            Chart Area (Coming Soon)
          </div>
          <div className="h-64 bg-slate-900/50 rounded-xl border border-slate-800 flex items-center justify-center text-slate-500 border-dashed">
            Chart Area (Coming Soon)
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
