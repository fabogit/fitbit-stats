import { TrendChart } from "../charts/TrendChart";
import { EnergyChart } from "../charts/EnergyChart";
import { WeightChart } from "../charts/WeightChart";

export function TimelineView() {
  const SYNC_ID = "main-timeline-sync";

  return (
    <div className="space-y-6">
      {/* Row 1: Readiness & RHR */}
      <TrendChart syncId={SYNC_ID} />

      {/* Row 2: Energy (BMR vs Active) */}
      <EnergyChart syncId={SYNC_ID} />

      {/* Row 3: Weight */}
      <WeightChart syncId={SYNC_ID} />
    </div>
  );
}
