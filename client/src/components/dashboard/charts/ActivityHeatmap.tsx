import { useMemo, cloneElement } from "react";
import { ActivityCalendar, type ThemeInput } from "react-activity-calendar";
import { Tooltip as ReactTooltip } from "react-tooltip";
import { useAppSelector } from "@/store/store";
import { selectResolvedTheme } from "@/store/slices/themeSlice";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { cn } from "@/lib/utils";

export function ActivityHeatmap() {
  const { filteredData } = useAppSelector((state) => state.dashboard);
  const resolvedTheme = useAppSelector(selectResolvedTheme);

  const calendarData = useMemo(() => {
    return filteredData.map((d) => {
      const mins = d.very_active_minutes || 0;
      let level = 0;
      if (mins > 0) level = 1;
      if (mins > 30) level = 2;
      if (mins > 60) level = 3;
      if (mins > 90) level = 4;

      return {
        date: d.date,
        count: mins,
        level: level,
      };
    });
  }, [filteredData]);

  const colorTheme: ThemeInput = {
    dark: ["#334155", "#064e3b", "#065f46", "#10b981", "#34d399"],
    light: ["#e2e8f0", "#bbf7d0", "#86efac", "#22c55e", "#15803d"],
  };

  const isMobile = useMediaQuery("(max-width: 640px)");
  const blockSize = isMobile ? 8 : 12;
  const blockMargin = isMobile ? 2 : 3;

  return (
    <div className="bg-card border border-border rounded-xl p-4 md:p-6 shadow-sm overflow-hidden h-full flex flex-col">
      <div className="flex items-center mb-4 md:mb-6">
        <h3 className="text-base md:text-lg font-semibold text-card-foreground">
          Workout Consistency
        </h3>
        <InfoTooltip
          side="bottom"
          content={
            <span>
              History of your <strong>Very Active Minutes</strong> based on
              selected range.
              <br />
              Darker green = More intense workout.
            </span>
          }
        />
      </div>

      <div className="w-full overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-muted">
        <div className={cn(isMobile ? "w-full" : "min-w-[800px]", "flex justify-center md:justify-start")}>
          {calendarData.length > 0 ? (
            <ActivityCalendar
              data={calendarData}
              theme={colorTheme}
              colorScheme={resolvedTheme}
              blockRadius={2}
              blockSize={blockSize}
              blockMargin={blockMargin}
              fontSize={isMobile ? 10 : 12}
              showWeekdayLabels={!isMobile}
              showTotalCount={false}
              renderBlock={(block, activity) =>
                cloneElement(block, {
                  "data-tooltip-id": "calendar-tooltip",
                  "data-tooltip-content": `${activity.date}: ${activity.count} min`,
                })
              }
            />
          ) : (
            <div className="text-muted-foreground text-sm py-10 text-center bg-muted/30 rounded-lg border border-dashed border-border">
              No activity data available for this period.
            </div>
          )}
        </div>
      </div>

      <ReactTooltip
        id="calendar-tooltip"
        border="1px solid hsl(var(--border))"
        style={{
          backgroundColor: "hsl(var(--popover))",
          color: "hsl(var(--popover-foreground))",
          fontSize: "12px",
          borderRadius: "6px",
          padding: "8px",
          zIndex: 50,
        }}
      />
    </div>
  );
}
