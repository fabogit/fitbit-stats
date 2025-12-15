import { useState, useCallback } from "react";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { setDateRange } from "@/features/dashboard/dashboardSlice";
import { Calendar, Clock, Filter } from "lucide-react";
import {
  subMonths,
  parseISO,
  format,
  startOfYear,
  differenceInDays,
} from "date-fns";
import { cn } from "@/lib/utils";

export function DateFilter() {
  const dispatch = useAppDispatch();
  const { dateRange, data } = useAppSelector((state) => state.dashboard);
  const [activePreset, setActivePreset] = useState<string>("3M");

  const minDate = data.length > 0 ? data[0].date : "";
  const lastDataDate = data.length > 0 ? data[data.length - 1].date : "";
  const today = format(new Date(), "yyyy-MM-dd");
  const maxDate = lastDataDate > today ? today : lastDataDate;

  const presets = [
    { label: "1M", months: 1 },
    { label: "3M", months: 3 },
    { label: "6M", months: 6 },
    { label: "1Y", months: 12 },
    { label: "YTD", months: 0, type: "ytd" },
    { label: "ALL", months: 0, type: "all" },
  ];

  const applyPreset = useCallback(
    (months: number, type?: string, label?: string) => {
      if (!data.length) return;
      const endObj = parseISO(maxDate);
      let startObj;
      if (type === "all") startObj = parseISO(minDate);
      else if (type === "ytd") startObj = startOfYear(endObj);
      else startObj = subMonths(endObj, months);

      let newStart = format(startObj, "yyyy-MM-dd");
      if (newStart < minDate) newStart = minDate;

      dispatch(setDateRange({ start: newStart, end: maxDate }));
      if (label) setActivePreset(label);
    },
    [data, dispatch, maxDate, minDate]
  );

  if (!dateRange || data.length === 0) return null;

  return (
    <div className="space-y-6">
      {/* 1. Data Range Info */}
      <div className="bg-muted/50 p-3 rounded-lg border border-border">
        <div className="flex items-center gap-2 text-muted-foreground mb-1">
          <Clock className="w-3 h-3" />
          <span className="text-[10px] uppercase font-bold tracking-wider">
            Available Data
          </span>
        </div>
        <div className="text-xs text-foreground font-mono">
          {minDate} <span className="text-muted-foreground">to</span> {maxDate}
        </div>
        <div className="text-[10px] text-muted-foreground mt-1">
          {differenceInDays(parseISO(maxDate), parseISO(minDate))} days total
        </div>
      </div>

      {/* 2. Selected Period Info */}
      <div className="bg-primary/10 p-3 rounded-lg border border-primary/20">
        <div className="flex items-center gap-2 text-primary mb-1">
          <Filter className="w-3 h-3" />
          <span className="text-[10px] uppercase font-bold tracking-wider">
            Selected Period
          </span>
        </div>
        <div className="text-xs text-foreground font-mono">
          {dateRange.start} <span className="text-muted-foreground">to</span>{" "}
          {dateRange.end}
        </div>
        <div className="text-[10px] text-primary/80 mt-1">
          {differenceInDays(parseISO(dateRange.end), parseISO(dateRange.start))}{" "}
          days selected
        </div>
      </div>

      <div className="space-y-3">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-1">
          Quick Filters
        </div>

        {/* Presets Grid */}
        <div className="grid grid-cols-3 gap-2">
          {presets.map((preset) => (
            <button
              key={preset.label}
              onClick={() =>
                applyPreset(preset.months, preset.type, preset.label)
              }
              className={cn(
                "px-2 py-1.5 text-xs font-medium rounded border transition-all duration-200",
                activePreset === preset.label
                  ? "bg-primary text-primary-foreground border-primary shadow-md"
                  : "bg-card text-card-foreground border-border hover:bg-accent hover:text-accent-foreground"
              )}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Manual Inputs */}
      <div className="space-y-2 pt-2 border-t border-border">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-1 mb-2">
          Custom Range
        </div>
        <div className="flex items-center gap-2 bg-card p-2 rounded border border-input group focus-within:border-primary/50 transition-colors">
          <Calendar className="w-3 h-3 text-muted-foreground group-focus-within:text-primary" />
          <input
            type="date"
            className="bg-transparent text-xs text-foreground focus:outline-none w-full cursor-pointer p-0"
            value={dateRange.start}
            min={minDate}
            max={maxDate}
            onChange={(e) => {
              dispatch(
                setDateRange({ start: e.target.value, end: dateRange.end })
              );
              setActivePreset("CUSTOM");
            }}
          />
        </div>
        <div className="flex items-center gap-2 bg-card p-2 rounded border border-input group focus-within:border-primary/50 transition-colors">
          <Calendar className="w-3 h-3 text-muted-foreground group-focus-within:text-primary" />
          <input
            type="date"
            className="bg-transparent text-xs text-foreground focus:outline-none w-full cursor-pointer p-0"
            value={dateRange.end}
            min={minDate}
            max={maxDate}
            onChange={(e) => {
              let val = e.target.value;
              if (val > maxDate) val = maxDate;
              dispatch(setDateRange({ start: dateRange.start, end: val }));
              setActivePreset("CUSTOM");
            }}
          />
        </div>
      </div>
    </div>
  );
}
