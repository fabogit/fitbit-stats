import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "./store";
import { fetchHealthData } from "./features/dashboard/dashboardSlice";
import { Header } from "./components/dashboard/Header";
import { KpiGrid } from "./components/dashboard/KpiGrid";

// Charts
import { TrendChart } from "./components/dashboard/charts/TrendChart";
import { EnergyChart } from "./components/dashboard/charts/EnergyChart";
import { ZonesChart } from "./components/dashboard/charts/ZonesChart";
import { WeightChart } from "./components/dashboard/charts/WeightChart";
import { ScatterChart } from "./components/dashboard/charts/ScatterChart";

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
    <div className="min-h-screen bg-slate-950 p-4 md:p-8 text-slate-50">
      <div className="max-w-7xl mx-auto space-y-6">
        <Header />

        <KpiGrid />

        {/* Row 1: Main Trends */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TrendChart />
          <EnergyChart />
        </div>

        {/* Row 2: Secondary Analysis */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Zones chart is smaller, maybe give it 1 column */}
          <div className="lg:col-span-1">
            <ZonesChart />
          </div>
          {/* Weight chart takes more space */}
          <div className="lg:col-span-2">
            <WeightChart />
          </div>
        </div>

        {/* Row 3: Correlations */}
        <div className="grid grid-cols-1">
          <ScatterChart />
        </div>
      </div>
    </div>
  );
}

export default App;
