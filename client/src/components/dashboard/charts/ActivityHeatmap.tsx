import { useMemo, cloneElement } from "react";
import { ActivityCalendar, type ThemeInput } from "react-activity-calendar";
import { Tooltip as ReactTooltip } from "react-tooltip";
import { useAppSelector } from "@/store";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

export function ActivityHeatmap() {
  const { filteredData } = useAppSelector((state) => state.dashboard);

  const calendarData = useMemo(() => {
    return filteredData.map((d) => {
      const mins = d.very_active_minutes || 0;
      let level = 0;

      if (mins > 0) level = 1;
      if (mins > 30) level = 2;
      if (mins > 60) level = 3;
      if (mins > 90) level = 4;
      if (mins > 120) level = 5;
      if (mins > 150) level = 6;

      return {
        date: d.date,
        count: mins,
        level: level,
      };
    });
  }, [filteredData]);

  const colorTheme: ThemeInput = {
    dark: [
      "#1e293b", // Level 0: Slate-800 (Empty)
      "#064e3b", // Level 1: Emerald-950 (Very Dark Green)
      "#065f46", // Level 2: Emerald-900
      "#047857", // Level 3: Emerald-700
      "#10b981", // Level 4: Emerald-500
      "#34d399", // Level 5: Emerald-400
      "#6ee7b7", // Level 6: Emerald-300 (Brightest/Neon)
    ],
    light: [
      "#ebedf0", // Level 0
      "#c6e48b", // Level 1
      "#7bc96f", // Level 2
      "#239a3b", // Level 3
      "#196127", // Level 4
      "#0f3d1f", // Level 5
      "#05220d", // Level 6
    ],
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
      <div className="flex items-center mb-6">
        <h3 className="text-lg font-semibold text-slate-100">
          Workout Consistency
        </h3>
        <InfoTooltip
          content={
            <span>
              History of your <strong>Very Active Minutes</strong> based on
              selected range.
              <br />
              Lighter green = More intense workout (7 levels).
            </span>
          }
        />
      </div>

      <div className="w-full overflow-x-auto pb-2">
        <div className="min-w-[800px]">
          {calendarData.length > 0 ? (
            <ActivityCalendar
              data={calendarData}
              theme={colorTheme}
              colorScheme="dark"
              blockRadius={3}
              blockSize={12}
              blockMargin={3}
              fontSize={12}
              showWeekdayLabels={true}
              showTotalCount={false}
              maxLevel={6}
              renderBlock={(block, activity) =>
                cloneElement(block, {
                  "data-tooltip-id": "calendar-tooltip",
                  "data-tooltip-content": `${activity.date}: ${activity.count} min`,
                })
              }
            />
          ) : (
            <div className="text-slate-500 text-sm py-10 text-center bg-slate-950/30 rounded-lg border border-dashed border-slate-800">
              No activity data available for this period.
            </div>
          )}
        </div>
      </div>

      <ReactTooltip
        id="calendar-tooltip"
        style={{
          backgroundColor: "#1e293b",
          color: "#fff",
          fontSize: "12px",
          borderRadius: "6px",
          padding: "8px",
          zIndex: 50,
        }}
      />
    </div>
  );
}
