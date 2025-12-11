import {
  LayoutDashboard,
  Activity,
  PieChart,
  PanelLeftClose,
} from "lucide-react";
import { DateFilter } from "./DateFilter";
import { cn } from "@/lib/utils";

interface SidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  onClose: () => void; // <--- Nuova prop
}

export function Sidebar({ currentTab, onTabChange, onClose }: SidebarProps) {
  const navItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "timeline", label: "Timeline", icon: Activity },
    { id: "analytics", label: "Analytics", icon: PieChart },
  ];

  return (
    <aside className="flex flex-col h-full overflow-y-auto">
      {/* Logo Area & Close Button */}
      <div className="p-6 border-b border-slate-800 flex items-center justify-between">
        <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
          🚵🏃‍♂️🏋️{" "}
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400">
            FitStats
          </span>
        </h1>

        {/* Bottone CHIUDI (Dentro la navbar) */}
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-white transition-colors p-1 rounded hover:bg-slate-800"
          title="Close Sidebar"
        >
          <PanelLeftClose className="w-5 h-5" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-1 flex-1">
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 px-2">
          Menu
        </div>
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onTabChange(item.id)}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200",
              currentTab === item.id
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-900/20"
                : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
            )}
          >
            <item.icon className="w-4 h-4" />
            {item.label}
          </button>
        ))}
      </nav>

      {/* Filters Section (Bottom) */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/50">
        <DateFilter />
      </div>
    </aside>
  );
}
