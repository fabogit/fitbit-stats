import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "./store";
import { fetchHealthData } from "./features/dashboard/dashboardSlice";
import { Header } from "./components/dashboard/Header";
import { KpiGrid } from "./components/dashboard/KpiGrid";
import { TrendChart } from "./components/dashboard/charts/TrendChart";
import { EnergyChart } from "./components/dashboard/charts/EnergyChart";

function App() {
  const dispatch = useAppDispatch();
  const { status, error } = useAppSelector((state) => state.dashboard);

  useEffect(() => {
    dispatch(fetchHealthData());
  }, [dispatch]);

  if (status === "loading") {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
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
    <div className="min-h-screen bg-slate-950 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        <Header />
        <main>
          <KpiGrid />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <TrendChart />
            <EnergyChart />
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
