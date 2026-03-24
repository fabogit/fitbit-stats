import {
  LayoutDashboard,
  Activity,
  PieChart,
  Table,
  Settings,
} from "lucide-react";
import { DateFilter } from "./DateFilter";
import { cn } from "@/lib/utils";

interface SidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
}

export function Sidebar({ currentTab, onTabChange }: SidebarProps) {
  const navItems = [
    { id: "settings", label: "Calculate / Edit", icon: Settings },
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "timeline", label: "Timeline", icon: Activity },
    { id: "analytics", label: "Analytics", icon: PieChart },
    { id: "brief", label: "Daily Brief", icon: Activity },
    { id: "datagrid", label: "Data Grid", icon: Table },
  ];

  return (
    <aside className="flex flex-col h-full overflow-y-auto bg-card border-r border-border">
      {/* Logo Area */}
      <div className="p-6 border-b border-border flex items-center justify-between">
        <h1 className="text-xl font-bold text-foreground tracking-tight flex items-center gap-2">
          🏃‍♂️{" "}
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400">
            FitStats
          </span>
        </h1>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-1 flex-1">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-2">
          Menu
        </div>
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onTabChange(item.id)}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200",
              currentTab === item.id
                ? "bg-primary text-primary-foreground shadow-md"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <item.icon className="w-4 h-4" />
            {item.label}
          </button>
        ))}
      </nav>

      {/* Footer Section: Filters */}
      <div className="p-4 border-t border-border bg-muted/20 space-y-4">
        {/* Date Filter Component */}
        <DateFilter />
      </div>
    </aside>
  );
}
