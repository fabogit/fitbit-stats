import { Info } from "lucide-react";
import { Tooltip as ReactTooltip } from "react-tooltip";
import { useId } from "react";

interface InfoTooltipProps {
  content: React.ReactNode;
  side?: "top" | "top-start" | "top-end" | "bottom" | "bottom-start" | "bottom-end" | "left" | "right";
}

export function InfoTooltip({ content, side = "bottom-start" }: InfoTooltipProps) {
  const id = useId();

  return (
    <div className="inline-flex ml-2 items-center cursor-help">
      <Info 
        className="w-4 h-4 text-slate-500 hover:text-indigo-400 transition-colors" 
        data-tooltip-id={`info-tooltip-${id}`}
      />

      <ReactTooltip
        id={`info-tooltip-${id}`}
        place={side}
        variant="dark"
        className="z-[100] !max-w-[280px] !p-3 !bg-slate-800 !border !border-slate-700 !text-slate-200 !text-xs !rounded-lg !shadow-xl !opacity-100 !visible pointer-events-none"
        style={{
          backgroundColor: 'hsl(var(--slate-800))',
          color: 'hsl(var(--slate-200))',
          zIndex: 100,
        }}
      >
        <div className="leading-relaxed">
          {content}
        </div>
      </ReactTooltip>
    </div>
  );
}
