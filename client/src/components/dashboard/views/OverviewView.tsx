import { KpiGrid } from "../KpiGrid";

export function OverviewView() {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Health Overview</h2>
        <p className="text-slate-400">
          Key metrics summary for the selected period.
        </p>
      </div>

      {/* Qui ci sono le card */}
      <KpiGrid />

      {/* Possiamo aggiungere qui un testo o un grafico riassuntivo veloce in futuro */}
    </div>
  );
}
