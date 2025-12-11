import { useState, useEffect } from "react";
import { TrendChart } from "../charts/TrendChart";
import { EnergyChart } from "../charts/EnergyChart";
import { WeightChart } from "../charts/WeightChart";
import { SleepChart } from "../charts/SleepChart";
import { PhysiologyChart } from "../charts/PhysiologyChart";
import { ChartWrapper } from "../ChartWrapper";

type ChartKey = "trend" | "physiology" | "sleep" | "energy" | "weight";

export function TimelineView() {
  const SYNC_ID = "main-timeline-sync";
  const STORAGE_KEY = "fitbit-timeline-order";

  const defaultOrder: ChartKey[] = [
    "trend",
    "physiology",
    "sleep",
    "energy",
    "weight",
  ];

  const [chartOrder, setChartOrder] = useState<ChartKey[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.length === defaultOrder.length) return parsed;
      } catch (e) {
        console.error("Error parsing saved chart order", e);
      }
    }
    return defaultOrder;
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chartOrder));
  }, [chartOrder]);

  const moveUp = (index: number) => {
    if (index === 0) return;
    const newOrder = [...chartOrder];
    [newOrder[index - 1], newOrder[index]] = [
      newOrder[index],
      newOrder[index - 1],
    ];
    setChartOrder(newOrder);
  };

  const moveDown = (index: number) => {
    if (index === chartOrder.length - 1) return;
    const newOrder = [...chartOrder];
    [newOrder[index + 1], newOrder[index]] = [
      newOrder[index],
      newOrder[index + 1],
    ];
    setChartOrder(newOrder);
  };

  const chartComponents: Record<ChartKey, React.ReactNode> = {
    trend: <TrendChart syncId={SYNC_ID} />,
    physiology: <PhysiologyChart syncId={SYNC_ID} />,
    sleep: <SleepChart syncId={SYNC_ID} />,
    energy: <EnergyChart syncId={SYNC_ID} />,
    weight: <WeightChart syncId={SYNC_ID} />,
  };

  return (
    <div className="space-y-6 pb-10">
      {chartOrder.map((key, index) => (
        <ChartWrapper
          key={key}
          isFirst={index === 0}
          isLast={index === chartOrder.length - 1}
          onMoveUp={() => moveUp(index)}
          onMoveDown={() => moveDown(index)}
        >
          {chartComponents[key]}
        </ChartWrapper>
      ))}
    </div>
  );
}
