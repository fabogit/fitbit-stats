import { useAppDispatch, useAppSelector } from "@/store";
import { setDateRange, resetFilter } from "@/features/dashboard/dashboardSlice";
import { Calendar } from "lucide-react";

export function Header() {
  const dispatch = useAppDispatch();
  const { dateRange, data } = useAppSelector((state) => state.dashboard);

  if (!dateRange || data.length === 0) return null;

  const minDate = data[0].date;
  const maxDate = data[data.length - 1].date;

  const handleStartChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setDateRange({ start: e.target.value, end: dateRange.end }));
  };

  const handleEndChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setDateRange({ start: dateRange.start, end: e.target.value }));
  };

  return (
    <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">
          🏃‍♂️ Personal Health
        </h1>
        <p className="text-slate-400 mt-1">
          Analysis from{" "}
          <span className="font-mono text-slate-200">{minDate}</span> to{" "}
          <span className="font-mono text-slate-200">{maxDate}</span>
        </p>
      </div>

      <div className="flex items-center gap-2 bg-slate-900 p-2 rounded-lg border border-slate-800">
        <Calendar className="w-4 h-4 text-slate-500 ml-2" />

        {/* Native Date Inputs styled with Tailwind */}
        <input
          type="date"
          value={dateRange.start}
          min={minDate}
          max={maxDate}
          onChange={handleStartChange}
          className="bg-transparent text-sm text-slate-200 border-none focus:ring-0 cursor-pointer [&::-webkit-calendar-picker-indicator]:invert"
        />
        <span className="text-slate-600">-</span>
        <input
          type="date"
          value={dateRange.end}
          min={minDate}
          max={maxDate}
          onChange={handleEndChange}
          className="bg-transparent text-sm text-slate-200 border-none focus:ring-0 cursor-pointer [&::-webkit-calendar-picker-indicator]:invert"
        />

        <button
          onClick={() => dispatch(resetFilter())}
          className="ml-2 text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded transition-colors"
        >
          Reset
        </button>
      </div>
    </header>
  );
}
