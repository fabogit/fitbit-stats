import { Info } from "lucide-react";
import { Tooltip as ReactTooltip } from "react-tooltip";
import { useId } from "react";

interface InfoTooltipProps {
  content: React.ReactNode;
  side?: "top" | "bottom" | "left" | "right";
}

export function InfoTooltip({ content, side = "top" }: InfoTooltipProps) {
  const id = useId();

  return (
    <>
      <button
        data-tooltip-id={id}
        type="button"
        className="inline-flex ml-2 items-center text-slate-500 hover:text-indigo-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 rounded-full"
        aria-label="More information"
      >
        <Info className="w-4 h-4" />
      </button>

      <ReactTooltip
        id={id}
        place={side}
        clickable
        className="z-50 !max-w-xs !bg-slate-800 !text-slate-200 !text-xs !rounded-lg !shadow-xl !px-3 !py-3 !border !border-slate-700 !opacity-100"
      >
        {content}
      </ReactTooltip>
    </>
  );
}
