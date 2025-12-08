import { useAppDispatch, useAppSelector } from "@/store";
import { setDateRange } from "@/features/dashboard/dashboardSlice";
import { Calendar, Clock } from "lucide-react";
import { subMonths, parseISO, format, startOfYear } from "date-fns";

export function Header() {
  const dispatch = useAppDispatch();
  const { dateRange, data } = useAppSelector((state) => state.dashboard);

  if (!dateRange || data.length === 0) return null;

  const minDate = data[0].date;
  const lastDataDate = data[data.length - 1].date;
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

  const applyPreset = (months: number, type?: string) => {
    const endObj = parseISO(maxDate);
    let startObj;

    if (type === "all") {
      startObj = parseISO(minDate);
    } else if (type === "ytd") {
      startObj = startOfYear(endObj);
    } else {
      startObj = subMonths(endObj, months);
    }

    let newStart = format(startObj, "yyyy-MM-dd");

    if (newStart < minDate) newStart = minDate;

    dispatch(setDateRange({ start: newStart, end: maxDate }));
  };

  const handleStartChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setDateRange({ start: e.target.value, end: dateRange.end }));
  };

  const handleEndChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let newEnd = e.target.value;
    if (newEnd > maxDate) newEnd = maxDate; // Force clamp

    dispatch(setDateRange({ start: dateRange.start, end: newEnd }));
  };

  return (
    <header className="flex flex-col xl:flex-row xl:items-end justify-between gap-6 mb-8">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">
          🏃‍♂️ Personal Health
        </h1>
        <p className="text-slate-400 mt-1 flex items-center gap-2">
          <Clock className="w-4 h-4" />
          <span>
            Data Range:{" "}
            <span className="font-mono text-slate-200">{minDate}</span> to{" "}
            <span className="font-mono text-slate-200">{maxDate}</span>
          </span>
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        {/* Quick Select Buttons */}
        <div className="flex bg-slate-900 p-1 rounded-lg border border-slate-800 self-start sm:self-center">
          {presets.map((preset) => (
            <button
              key={preset.label}
              onClick={() => applyPreset(preset.months, preset.type)}
              className="px-3 py-1.5 text-xs font-medium rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-all focus:outline-none focus:bg-slate-700 active:bg-indigo-600 active:text-white"
            >
              {preset.label}
            </button>
          ))}
        </div>

        {/* Custom Date Inputs */}
        <div className="flex items-center gap-2 bg-slate-900 p-2 rounded-lg border border-slate-800">
          <Calendar className="w-4 h-4 text-slate-500 ml-2" />

          <input
            type="date"
            value={dateRange.start}
            min={minDate}
            max={maxDate}
            onChange={handleStartChange}
            className="bg-transparent text-sm text-slate-200 border-none focus:ring-0 cursor-pointer [&::-webkit-calendar-picker-indicator]:invert p-0 w-28"
          />
          <span className="text-slate-600">-</span>
          <input
            type="date"
            value={dateRange.end}
            min={minDate}
            max={maxDate}
            onChange={handleEndChange}
            className="bg-transparent text-sm text-slate-200 border-none focus:ring-0 cursor-pointer [&::-webkit-calendar-picker-indicator]:invert p-0 w-28"
          />
        </div>
      </div>
    </header>
  );
}
